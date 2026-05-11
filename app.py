import openai
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, RichLog, Input

client = openai.OpenAI(
    api_key="sk-462e17eb90454973a6aaea3c08e04309",
    base_url="https://api.deepseek.com"
)

class Daedalus(App):
    BINDINGS = [("q", "quit", "Quitter")]
    CSS = "RichLog { background: #0d1117; color: #58a6ff; } Input { dock: bottom; }"
    history = [{"role": "system", "content": "Tu es Daedalus."}]

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(markup=True, wrap=True)
        yield Input(placeholder="Ecris ici...")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        log = self.query_one(RichLog)
        msg = event.value.strip()
        if msg:
            self.query_one(Input).value = ""
            log.write(f"Moi : {msg}")
            self.history.append({"role": "user", "content": msg})
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=self.history
                )
                answer = response.choices[0].message.content
                self.history.append({"role": "assistant", "content": answer})
                log.write(f"Daedalus : {answer}")
            except Exception as e:
                log.write(f"Erreur : {e}")

if __name__ == "__main__":
    Daedalus().run()

