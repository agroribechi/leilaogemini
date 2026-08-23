from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from PIL import ImageTk

from leilao_ocr.capture import ScreenCapture
from leilao_ocr.config import ConfigStore, REGION_NAMES
from leilao_ocr.history import HistoryRepository
from leilao_ocr.models import Reading, Region
from leilao_ocr.normalization import normalize_description, normalize_lot, normalize_price_cents
from leilao_ocr.ocr import TesseractReader
from leilao_ocr.operations import AuctionStore, OperationStore
from leilao_ocr.publisher import publisher_from_environment
from leilao_ocr.ai import refine_with_gemini
import threading

ROOT = Path(__file__).parent
DATA = ROOT / "data"
COLORS = {"video": "#5bc0de", "lot": "#f0ad4e", "price": "#5cb85c", "description": "#d9534f"}


class CalibrationWindow(tk.Toplevel):
    def __init__(self, master: "AuctionApp", screenshot, screen_bounds: Region) -> None:
        super().__init__(master)
        self.master = master
        self.screenshot = screenshot
        self.screen_bounds = screen_bounds
        self.title("Calibração — desenhe as quatro regiões")
        self.active = tk.StringVar(value="video")
        self.start: tuple[int, int] | None = None
        self.rect_id: int | None = None
        # Usa quase toda a tela disponível, preservando espaço para os controles.
        max_width = max(1180, self.winfo_screenwidth() - 100)
        max_height = max(720, self.winfo_screenheight() - 190)
        self.scale = min(1, max_width / screenshot.width, max_height / screenshot.height)
        displayed = screenshot.resize((int(screenshot.width * self.scale), int(screenshot.height * self.scale)))
        self.photo = ImageTk.PhotoImage(displayed)
        controls = ttk.Frame(self); controls.pack(fill="x", padx=8, pady=8)
        for name, label in (("video", "1. Área do vídeo"), ("lot", "2. Lote"), ("price", "3. Preço"), ("description", "4. Descrição")):
            ttk.Radiobutton(controls, text=label, variable=self.active, value=name).pack(side="left", padx=5)
        ttk.Button(controls, text="Salvar calibração", command=self.save).pack(side="right")
        ttk.Label(self, text="Escolha uma região acima e arraste sobre a tela. As regiões Lote, Preço e Descrição devem ficar dentro da área do vídeo.").pack(padx=8, pady=(0, 8))
        self.canvas = tk.Canvas(self, width=displayed.width, height=displayed.height, cursor="crosshair")
        self.canvas.pack(padx=8, pady=(0, 8))
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        self.draw_existing()
        self.canvas.bind("<ButtonPress-1>", self.begin)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.end)
        self.transient(master)
        self.grab_set()

    def draw_existing(self) -> None:
        for name, region in self.master.regions.items():
            self.draw_region(name, region)

    def draw_region(self, name: str, region: Region) -> None:
        x1, y1 = (region.left - self.screen_bounds.left) * self.scale, (region.top - self.screen_bounds.top) * self.scale
        x2, y2 = (region.left + region.width - self.screen_bounds.left) * self.scale, (region.top + region.height - self.screen_bounds.top) * self.scale
        self.canvas.create_rectangle(x1, y1, x2, y2, outline=COLORS[name], width=3, tags=(f"region-{name}",))
        self.canvas.create_text(x1 + 5, y1 + 10, anchor="w", text=name, fill=COLORS[name], font=("Segoe UI", 10, "bold"), tags=(f"region-{name}",))

    def begin(self, event) -> None:
        self.start = (event.x, event.y)
        self.canvas.delete("selection")
        self.rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline=COLORS[self.active.get()], width=3, tags="selection")

    def drag(self, event) -> None:
        if self.start and self.rect_id:
            self.canvas.coords(self.rect_id, self.start[0], self.start[1], event.x, event.y)

    def end(self, event) -> None:
        if not self.start:
            return
        x1, y1 = self.start; x2, y2 = event.x, event.y
        left, top = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)
        if width < 8 or height < 8:
            return
        name = self.active.get()
        self.master.regions[name] = Region(
            self.screen_bounds.left + round(left / self.scale),
            self.screen_bounds.top + round(top / self.scale),
            round(width / self.scale),
            round(height / self.scale),
        )
        self.canvas.delete(f"region-{name}")
        self.draw_region(name, self.master.regions[name])
        self.start = None

    def save(self) -> None:
        missing = set(REGION_NAMES) - set(self.master.regions)
        if missing:
            messagebox.showwarning("Calibração incompleta", "Faltam: " + ", ".join(missing), parent=self)
            return
        self.master.config_store.save(self.master.regions)
        self.master.status.set("Calibração salva. Inicie a leitura.")
        self.destroy()


class AuctionApp(tk.Tk):
    def __init__(self, tesseract_path: str | None = None) -> None:
        super().__init__()
        self.title("Leilão OCR — MVP local")
        self.geometry("1050x720")
        self.capture = ScreenCapture(); self.reader = TesseractReader(tesseract_path)
        self.config_store = ConfigStore(DATA / "calibration.json")
        self.regions = self.config_store.load()
        self.history = HistoryRepository(DATA / "auction.db")
        self.auction_store = AuctionStore(DATA / "auctions.json")
        self.operation_store = OperationStore(DATA / "operation.json")
        self.auctions = self.auction_store.load()
        self.publisher = publisher_from_environment()
        self.sync_auctions_from_api()
        self.auction_var = tk.StringVar()
        self.select_initial_auction()
        self.running = False; self.last_signature = None; self.candidate = None; self.candidate_count = 0
        self.status = tk.StringVar(value="Calibre as regiões antes de iniciar.")
        self.current = {name: tk.StringVar(value="—") for name in ("lot", "price", "description")}
        self.build_ui(); self.refresh_history()

    def sync_auctions_from_api(self) -> None:
        if type(self.publisher).__name__ == "HttpPublisher":
            try:
                import json
                from urllib.request import Request, urlopen
                base = self.publisher.url.rsplit('/', 1)[0]
                req = Request(f"{base}/auctions", headers={"Accept": "application/json"})
                with urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        api_auctions = json.loads(resp.read().decode('utf-8'))
                        if api_auctions:
                            existing_ids = {a["id"] for a in self.auctions}
                            for a in api_auctions:
                                if a["id"] not in existing_ids:
                                    self.auctions.append(a)
                                    self.auction_store.add(a["name"], a["location"], auction_id=a["id"])
                            if hasattr(self, 'auction_picker'):
                                self.auction_picker.configure(values=self.auction_options())
            except Exception:
                pass

    def build_ui(self) -> None:
        operation = ttk.Labelframe(self, text="Operação do leilão", padding=10)
        operation.pack(fill="x", padx=12, pady=(10, 0))
        ttk.Label(operation, text="Leilão que receberá os dados:").pack(side="left")
        self.auction_picker = ttk.Combobox(operation, textvariable=self.auction_var, values=self.auction_options(), state="readonly", width=48)
        self.auction_picker.pack(side="left", padx=8)
        self.auction_picker.bind("<<ComboboxSelected>>", self.on_auction_change)
        ttk.Button(operation, text="Cadastrar leilão", command=self.register_auction).pack(side="left")
        mode = "● API em tempo real" if type(self.publisher).__name__ == "HttpPublisher" else "● Modo local"
        ttk.Label(operation, text=mode, foreground="#5b8c49").pack(side="right")
        top = ttk.Frame(self, padding=12); top.pack(fill="x")
        ttk.Button(top, text="Capturar e calibrar", command=self.calibrate).pack(side="left")
        ttk.Button(top, text="Limpar calibração", command=self.clear_calibration).pack(side="left", padx=(0, 8))
        self.start_button = ttk.Button(top, text="Iniciar leitura", command=self.toggle)
        self.start_button.pack(side="left", padx=8)
        ttk.Label(top, text="Leitura a cada 1,2 s; um dado precisa aparecer em 2 leituras para ser publicado.").pack(side="left", padx=8)
        content = ttk.Panedwindow(self, orient="horizontal"); content.pack(fill="both", expand=True, padx=12, pady=6)
        live = ttk.Labelframe(content, text="Leitura atual", padding=14); history = ttk.Labelframe(content, text="Eventos publicados", padding=10)
        content.add(live, weight=3); content.add(history, weight=2)
        ttk.Label(live, text="LOTE", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(live, textvariable=self.current["lot"], font=("Segoe UI", 28, "bold")).pack(anchor="w", pady=(0, 12))
        ttk.Label(live, text="PREÇO", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(live, textvariable=self.current["price"], font=("Segoe UI", 28, "bold")).pack(anchor="w", pady=(0, 12))
        ttk.Label(live, text="DESCRIÇÃO", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(live, textvariable=self.current["description"], wraplength=560, font=("Segoe UI", 14)).pack(anchor="w")
        columns = ("at", "lot", "price", "description")
        self.tree = ttk.Treeview(history, columns=columns, show="headings", height=20)
        for column, label, width in (("at", "Horário", 90), ("lot", "Lote", 55), ("price", "Preço", 95), ("description", "Descrição", 250)):
            self.tree.heading(column, text=label); self.tree.column(column, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w", padding=6).pack(fill="x", side="bottom")

    def calibrate(self) -> None:
        self.status.set("Capturando tela para calibração…")
        self.update_idletasks()
        try:
            bounds = self.capture.bounds()
            CalibrationWindow(self, self.capture.grab(bounds), bounds)
        except Exception as error:
            messagebox.showerror("Não foi possível capturar a tela", str(error), parent=self)

    def clear_calibration(self) -> None:
        if not messagebox.askyesno(
            "Limpar calibração",
            "Apagar todas as regiões salvas? A leitura ficará indisponível até uma nova calibração.",
            parent=self,
        ):
            return
        self.regions.clear()
        self.config_store.save(self.regions)
        self.running = False
        self.start_button.configure(text="Iniciar leitura")
        self.status.set("Calibração removida. Capture a tela para configurar novas regiões.")

    def toggle(self) -> None:
        if self.running:
            self.running = False; self.start_button.configure(text="Iniciar leitura"); self.status.set("Leitura pausada."); return
        missing = set(("lot", "price", "description")) - set(self.regions)
        if missing:
            messagebox.showwarning("Calibração necessária", "Defina: " + ", ".join(missing), parent=self); return
        self.running = True; self.start_button.configure(text="Pausar leitura"); self.read_once()

    def read_once(self) -> None:
        if not self.running: return
        try:
            raw = {name: self.reader.read(self.capture.grab(self.regions[name]), name) for name in ("lot", "price", "description")}
            auction = self.selected_auction()
            reading = Reading.now(lot=normalize_lot(raw["lot"]), price_cents=normalize_price_cents(raw["price"]), description=normalize_description(raw["description"]), raw_lot=raw["lot"], raw_price=raw["price"], raw_description=raw["description"], auction_id=auction["id"], auction_name=auction["name"])
            self.show(reading); self.process(reading)
        except Exception as error:
            self.status.set(f"Erro de OCR: {error}")
        self.after(1200, self.read_once)

    def show(self, reading: Reading) -> None:
        self.current["lot"].set(f"Lote {reading.lot}" if reading.lot is not None else "Não identificado")
        self.current["price"].set("—" if reading.price_cents is None else f"R$ {reading.price_cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self.current["description"].set(reading.description or "Não identificada")

    def process(self, reading: Reading) -> None:
        signature = (reading.lot, reading.price_cents, reading.description)
        if signature == self.candidate: self.candidate_count += 1
        else: self.candidate, self.candidate_count = signature, 1
        meaningful = reading.lot is not None or reading.price_cents is not None or bool(reading.description)
        
        if signature == self.last_signature:
            self.status.set("OCR ativo — mantendo leitura estável.")
        elif meaningful and self.candidate_count < 2:
            self.status.set(f"Leitura detectada (1/2): Lote {reading.lot or '—'} — aguardando confirmação...")
        elif meaningful and self.candidate_count >= 2 and signature != self.last_signature:
            self.last_signature = signature
            
            # Chama a IA e publica de forma assíncrona
            def refine_and_publish():
                try:
                    self.after(0, lambda: self.status.set("Avaliando com IA (Gemini)..."))
                    refined = refine_with_gemini(reading.raw_lot, reading.raw_price, reading.raw_description)
                    
                    final_reading = reading
                    if refined:
                        import dataclasses
                        final_reading = dataclasses.replace(
                            reading,
                            lot=refined.lot if refined.lot is not None else reading.lot,
                            price_cents=refined.price_cents if refined.price_cents is not None else reading.price_cents,
                            description=refined.description if refined.description is not None else reading.description
                        )
                    
                    self.history.add(final_reading)
                    self.after(0, self.refresh_history)
                    
                    try:
                        self.publisher.publish(final_reading)
                        self.after(0, lambda: self.status.set(f"✓ Lote {final_reading.lot or '—'} publicado na API com sucesso!"))
                    except Exception as pub_err:
                        err_msg = str(pub_err)
                        self.after(0, lambda m=err_msg: self.status.set(f"⚠ Salvo localmente, erro ao publicar na API: {m}"))
                except Exception as fatal_err:
                    err_msg = str(fatal_err)
                    self.after(0, lambda m=err_msg: self.status.set(f"⚠ Erro na gravação/processamento: {m}"))

            threading.Thread(target=refine_and_publish, daemon=True).start()

    def refresh_history(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for timestamp, lot, cents, description in self.history.recent(self.selected_auction()["id"]):
            price = "—" if cents is None else f"R$ {cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.tree.insert("", "end", values=(timestamp[11:19], lot or "—", price, description[:55]))

    def auction_options(self) -> list[str]:
        return [f"{auction['name']}  ·  {auction['location']}" for auction in self.auctions]

    def select_initial_auction(self) -> None:
        previous_id = self.operation_store.load_selected_id()
        selected = next((auction for auction in self.auctions if auction["id"] == previous_id), self.auctions[0])
        self.auction_var.set(f"{selected['name']}  ·  {selected['location']}")

    def selected_auction(self) -> dict[str, str]:
        return next(auction for auction in self.auctions if self.auction_var.get() == f"{auction['name']}  ·  {auction['location']}")

    def on_auction_change(self, _event=None) -> None:
        auction = self.selected_auction()
        self.operation_store.save_selected_id(auction["id"])
        self.last_signature = None
        self.candidate = None
        self.candidate_count = 0
        self.refresh_history()
        self.status.set(f"Leilão ativo: {auction['name']}. As próximas leituras serão vinculadas a ele.")

    def register_auction(self) -> None:
        name = simpledialog.askstring("Cadastrar leilão", "Nome do leilão:", parent=self)
        if not name:
            return
        location = simpledialog.askstring("Cadastrar leilão", "Cidade e estado (ex.: Uberaba, MG):", parent=self)
        if not location:
            return
        auction = self.auction_store.add(name, location)

        if type(self.publisher).__name__ == "HttpPublisher":
            try:
                import json
                from urllib.request import Request, urlopen
                base = self.publisher.url.rsplit('/', 1)[0]
                payload = json.dumps({"name": name, "location": location}).encode("utf-8")
                req = Request(f"{base}/auctions", data=payload, headers={"Content-Type": "application/json"}, method="POST")
                urlopen(req, timeout=3)
            except Exception:
                pass

        self.auctions = self.auction_store.load()
        self.auction_picker.configure(values=self.auction_options())
        self.auction_var.set(f"{auction['name']}  ·  {auction['location']}")
        self.on_auction_change()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tesseract", help="Caminho para tesseract.exe, caso não esteja no PATH")
    args = parser.parse_args()
    AuctionApp(args.tesseract).mainloop()
