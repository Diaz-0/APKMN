"""
Monitor de Red - Android
App Kivy para medir Ping en tiempo real.
Sin dependencias de psutil. Solo socket + time + threading.
"""

import socket
import time
import random
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.core.window import Window

# Forzar tamaño de ventana en modo escritorio (para pruebas)
Window.size = (400, 720)

# ==========================================
#  COLORES GLOBALES
# ==========================================
BG_COLOR       = (0.0706, 0.0706, 0.0863, 1)   # #121216
CARD_BG        = (0.1098, 0.1098, 0.1333, 1)    # Tarjetas oscuras
CARD_BORDER    = (0.22, 0.22, 0.25, 1)          # Bordes sutiles
TEXT_WHITE     = (0.95, 0.95, 0.95, 1)
TEXT_GRAY      = (0.55, 0.55, 0.58, 1)
GREEN          = (0.17, 0.88, 0.70, 1)          # #2CE0B3
PINK           = (0.78, 0.26, 0.96, 1)          # #C842F5
RED            = (1.0, 0.2, 0.2, 1)
YELLOW         = (1.0, 0.85, 0.2, 1)
BTN_GREEN      = (0.18, 0.72, 0.45, 1)
BTN_RED        = (0.85, 0.22, 0.22, 1)


# ==========================================
#  WIDGET: TARJETA CON BORDES REDONEADOS
# ==========================================
class RoundedCard(Widget):
    """Widget base que dibuja una tarjeta oscura con bordes redondeados."""

    def __init__(self, radius=16, bg_color=CARD_BG, border_color=CARD_BORDER, **kwargs):
        super().__init__(**kwargs)
        self._radius = radius
        self._bg_color = bg_color
        self._border_color = border_color
        self.bind(size=self._redraw, pos=self._redraw)
        self._redraw()

    def _redraw(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._bg_color)
            RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self._radius]
            )
            Color(*self._border_color)
            Line(
                rounded_rectangle=(
                    self.pos[0], self.pos[1],
                    self.size[0], self.size[1],
                    self._radius
                ),
                width=1.2,
            )

    def set_bg(self, color):
        self._bg_color = color
        self._redraw()


# ==========================================
#  WIDGET: TARJETA DE ESTADÍSTICA
# ==========================================
class StatCard(BoxLayout):
    def __init__(self, titulo, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.lbl_titulo = Label(
            text=titulo,
            font_size="13sp",
            bold=True,
            color=TEXT_GRAY,
            size_hint_y=0.35,
        )
        self.lbl_valor = Label(
            text="--",
            font_size="34sp",
            bold=True,
            color=TEXT_WHITE,
            size_hint_y=0.65,
        )
        self.add_widget(self.lbl_titulo)
        self.add_widget(self.lbl_valor)

    def set_value(self, valor, color=None):
        self.lbl_valor.text = str(valor)
        if color:
            self.lbl_valor.color = color

    def set_title_color(self, color):
        self.lbl_titulo.color = color


# ==========================================
#  PANTALLA PRINCIPAL
# ==========================================
class MonitorLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=0, spacing=0, **kwargs)

        # --- Estado ---
        self.monitoreando = False
        self.ping_ms = 0
        self.ping_lock = threading.Lock()
        self.datos = {"bajada": 0.0, "subida": 0.0}

        # --- Fondo ---
        with self.canvas.before:
            Color(*BG_COLOR)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size)
        self.bind(size=self._update_bg, pos=self._update_bg)

        # ==========================================
        #  TÍTULO
        # ==========================================
        self.add_widget(Label(
            text="MONITOR DE RED",
            font_size="22sp",
            bold=True,
            color=TEXT_WHITE,
            size_hint_y=0.08,
        ))

        # ==========================================
        #  TARJETA CENTRAL: PING + ESTADO
        # ==========================================
        card_ping_outer = BoxLayout(
            orientation="vertical", size_hint_y=0.38, padding=20
        )
        self.card_ping = RoundedCard(radius=20)

        inner_ping = BoxLayout(orientation="vertical")

        self.lbl_ping_label = Label(
            text="P I N G",
            font_size="14sp",
            bold=True,
            color=TEXT_GRAY,
            size_hint_y=0.15,
        )
        self.lbl_ping_valor = Label(
            text="--",
            font_size="72sp",
            bold=True,
            color=TEXT_WHITE,
            size_hint_y=0.50,
        )
        self.lbl_ping_unidad = Label(
            text="ms",
            font_size="16sp",
            color=TEXT_GRAY,
            size_hint_y=0.10,
        )
        self.lbl_estado = Label(
            text="Esperando...",
            font_size="14sp",
            bold=True,
            color=TEXT_GRAY,
            size_hint_y=0.25,
        )

        inner_ping.add_widget(self.lbl_ping_label)
        inner_ping.add_widget(self.lbl_ping_valor)
        inner_ping.add_widget(self.lbl_ping_unidad)
        inner_ping.add_widget(self.lbl_estado)
        self.card_ping.add_widget(inner_ping)
        card_ping_outer.add_widget(self.card_ping)
        self.add_widget(card_ping_outer)

        # ==========================================
        #  TARJETAS DE BAJADA Y SUBIDA
        # ==========================================
        row_stats = BoxLayout(
            orientation="horizontal", size_hint_y=0.20, padding=15, spacing=15
        )

        # Card Bajada
        bajada_outer = BoxLayout(orientation="vertical")
        card_bajada = RoundedCard(radius=14)
        self.stat_bajada = StatCard("↓  BAJADA")
        card_bajada.add_widget(self.stat_bajada)
        bajada_outer.add_widget(card_bajada)
        row_stats.add_widget(bajada_outer)

        # Card Subida
        subida_outer = BoxLayout(orientation="vertical")
        card_subida = RoundedCard(radius=14)
        self.stat_subida = StatCard("↑  SUBIDA")
        card_subida.add_widget(self.stat_subida)
        subida_outer.add_widget(card_subida)
        row_stats.add_widget(subida_outer)

        self.add_widget(row_stats)

        # ==========================================
        #  TARJETA: CONSUMO ACTUAL
        # ==========================================
        consumo_outer = BoxLayout(
            orientation="vertical", size_hint_y=0.14, padding=20
        )
        card_consumo = RoundedCard(radius=14)
        inner_consumo = BoxLayout(orientation="vertical")
        self.lbl_consumo_valor = Label(
            text="0.00",
            font_size="36sp",
            bold=True,
            color=GREEN,
            size_hint_y=0.6,
        )
        inner_consumo.add_widget(self.lbl_consumo_valor)
        inner_consumo.add_widget(Label(
            text="Consumo Actual (Mbps)",
            font_size="12sp",
            color=TEXT_GRAY,
            size_hint_y=0.4,
        ))
        card_consumo.add_widget(inner_consumo)
        consumo_outer.add_widget(card_consumo)
        self.add_widget(consumo_outer)

        # ==========================================
        #  BOTÓN DE INICIO / DETENER
        # ==========================================
        btn_outer = BoxLayout(
            orientation="vertical", size_hint_y=0.15, padding=(40, 5, 40, 15)
        )
        self.card_btn = RoundedCard(radius=30, bg_color=BTN_GREEN, border_color=BTN_GREEN)
        self.btn_label = Label(
            text="[  I N I C I O  ]",
            font_size="20sp",
            bold=True,
            color=TEXT_WHITE,
        )
        self.card_btn.add_widget(self.btn_label)
        btn_outer.add_widget(self.card_btn)
        self.add_widget(btn_outer)

        # Detectar toques en el botón
        self.card_btn.bind(on_touch_down=self._on_btn_press)

    # ==========================================
    #  FONDO RESPONSIVE
    # ==========================================
    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    # ==========================================
    #  LÓGICA DEL BOTÓN
    # ==========================================
    def _on_btn_press(self, instance, touch):
        if self.card_btn.collide_point(*touch.pos):
            self.toggle_monitoreo()
            return True
        return False

    def toggle_monitoreo(self):
        if not self.monitoreando:
            self.iniciar()
        else:
            self.detener()

    def iniciar(self):
        self.monitoreando = True
        self.btn_label.text = "[  D E T E N E R  ]"
        self.card_btn.set_bg(BTN_RED)
        self.card_btn._border_color = BTN_RED
        self.card_btn._redraw()

        # Resetear datos
        self.datos["bajada"] = 0.0
        self.datos["subida"] = 0.0

        t = threading.Thread(target=self._ping_loop, daemon=True)
        t.start()
        Clock.schedule_interval(self._actualizar_ui, 0.5)

    def detener(self):
        self.monitoreando = False
        self.btn_label.text = "[  I N I C I O  ]"
        self.card_btn.set_bg(BTN_GREEN)
        self.card_btn._border_color = BTN_GREEN
        self.card_btn._redraw()
        Clock.unschedule(self._actualizar_ui)

        self.lbl_ping_valor.text = "--"
        self.lbl_ping_valor.color = TEXT_WHITE
        self.lbl_estado.text = "Pausado"
        self.lbl_estado.color = TEXT_GRAY
        self.stat_bajada.set_value("--")
        self.stat_subida.set_value("--")
        self.lbl_consumo_valor.text = "0.00"

    # ==========================================
    #  HILO DE PING
    # ==========================================
    def _ping_loop(self):
        while self.monitoreando:
            ping = self._medir_ping()
            with self.ping_lock:
                self.ping_ms = ping
            time.sleep(1)

    @staticmethod
    def _medir_ping(host="8.8.8.8", port=53, timeout=3):
        try:
            inicio = time.time()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, port))
            s.close()
            ms = int((time.time() - inicio) * 1000)
            return min(ms, 999)
        except Exception:
            return 999

    # ==========================================
    #  ACTUALIZACIÓN DE UI
    # ==========================================
    def _actualizar_ui(self, dt):
        with self.ping_lock:
            ping = self.ping_ms

        # Semáforo de colores
        if ping < 100:
            color_ping = GREEN
            estado = "Conexión Estable"
            color_estado = GREEN
            icono = "🟢"
        elif ping < 250:
            color_ping = YELLOW
            estado = "Latencia Media"
            color_estado = YELLOW
            icono = "🟡"
        else:
            color_ping = RED
            estado = "Lag / Sin Conexión"
            color_estado = RED
            icono = "🔴"

        self.lbl_ping_valor.text = str(ping)
        self.lbl_ping_valor.color = color_ping
        self.lbl_estado.text = f"{icono}  {estado}"
        self.lbl_estado.color = color_estado

        # Simulación visual de bajada/subida (sin psutil en Android)
        with self.ping_lock:
            if self.monitoreando:
                b = max(0.0, self.datos["bajada"] + random.uniform(-2.0, 3.0))
                s = max(0.0, self.datos["subida"] + random.uniform(-1.0, 2.0))
                self.datos["bajada"] = round(b, 2)
                self.datos["subida"] = round(s, 2)
                bajada = b
                subida = s
            else:
                bajada = subida = 0.0

        self.stat_bajada.set_value(f"{bajada:.2f}")
        self.stat_bajada.set_title_color(GREEN)
        self.stat_subida.set_value(f"{subida:.2f}")
        self.stat_subida.set_title_color(PINK)
        self.lbl_consumo_valor.text = f"{bajada:.2f}"


# ==========================================
#  APP
# ==========================================
class MonitorRedApp(App):
    def build(self):
        self.title = "Monitor de Red"
        return MonitorLayout()


if __name__ == "__main__":
    MonitorRedApp().run()
