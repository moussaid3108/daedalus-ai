from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, RichLog, Input
from textual.containers import Container

class Daedalus(App):

    BINDINGS = [("q", "quit", "Quitter"), ("escape", "quit", "Quitter")]
    # Le style visuel (couleurs de l'interface)
    CSS = """
    RichLog {
        background: #0d1117;
        color: #58a6ff;
        border: double #30363d;
    }
    Input {
        dock: bottom;
        background: #161b22;
        color: white;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(RichLog(highlight=True, markup=True, id="chat_logs"))
        yield Input(placeholder="Entrez une commande pour Daedalus...")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        log.write("[bold cyan]SYSTÈME DAEDALUS v0.1[/]\n[gray]Architecte connecté. En attente de instructions...[/]")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        log = self.query_one(RichLog)
        if event.value.strip():
            log.write(f"> [yellow]{event.value}[/]")
            # Ici on ajoutera la connexion à l'IA plus tard
            log.write("[italic grey]Analyse en cours...[/]")
        event.input.value = ""

if __name__ == "__main__":
    app = Daedalus()
    app.run()

