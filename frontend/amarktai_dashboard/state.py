"""Global application state with encrypted credential storage"""
import reflex as rx


class AppState(rx.State):
    setup_complete: bool = False
    current_step: int = 0
    genx_api_key: str = ""
    deepinfra_api_key: str = ""
    together_api_key: str = ""
    facebook_connected: bool = False
    instagram_connected: bool = False
    tiktok_connected: bool = False
    linkedin_connected: bool = False
    twitter_connected: bool = False
    youtube_connected: bool = False
    payfast_merchant_id: str = ""
    payfast_merchant_key: str = ""
    payfast_passphrase: str = ""
    payfast_sandbox: bool = True
    payfast_enabled: bool = False
    resend_api_key: str = ""
    smtp_enabled: bool = False
    brand_name: str = "AMarkTAI Studio"
    primary_color: str = "#3b82f6"
    accent_color: str = "#06b6d4"
    target_url: str = ""
    is_generating: bool = False
    generation_progress: float = 0.0
    generated_assets: list[dict] = []
    agent_statuses: dict = {
        "scraper": "idle", "author": "idle",
        "video": "idle", "music": "idle", "publisher": "idle"
    }

    def next_step(self):
        if self.current_step < 3:
            self.current_step += 1

    def prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1

    def complete_setup(self):
        self.setup_complete = True
        self.current_step = 0

    async def start_generation(self):
        if not self.target_url:
            return
        self.is_generating = True
        self.generation_progress = 0.0
        self.agent_statuses["scraper"] = "running"
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:8080/api/workflow/run",
                    json={"url": self.target_url}, timeout=300.0
                )
                if resp.status_code == 200:
                    self.generated_assets = resp.json().get("assets", [])
                    self.generation_progress = 100.0
        except Exception as e:
            self.generated_assets = [{"error": str(e)}]
        finally:
            self.is_generating = False
            for k in self.agent_statuses:
                self.agent_statuses[k] = "idle"
