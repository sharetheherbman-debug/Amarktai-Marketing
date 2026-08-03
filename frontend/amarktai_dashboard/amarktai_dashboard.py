"""AMarkTAI Dashboard - Modern dark theme with animations"""
import reflex as rx
from .state import AppState

BG_DARK = "#0f172a"
BG_CARD = "rgba(30, 41, 59, 0.7)"
PRIMARY = "#3b82f6"
ACCENT = "#06b6d4"
VIOLET = "#8b5cf6"
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
GRADIENT_TEXT = "linear-gradient(135deg, #3b82f6, #06b6d4, #8b5cf6)"
GLASS_BORDER = "1px solid rgba(148, 163, 184, 0.1)"


def animated_bg():
    return rx.box(
        position="fixed", top="0", left="0", width="100vw", height="100vh", z_index="-1",
        background=f"radial-gradient(ellipse at 20% 50%, rgba(59,130,246,0.15) 0%, transparent 50%), "
                   f"radial-gradient(ellipse at 80% 20%, rgba(139,92,246,0.1) 0%, transparent 50%), "
                   f"radial-gradient(ellipse at 50% 80%, rgba(6,182,212,0.1) 0%, transparent 50%), "
                   f"{BG_DARK}",
    )


def glass_card(*children, **props):
    return rx.box(*children, background=BG_CARD, backdrop_filter="blur(12px)",
                  border=GLASS_BORDER, border_radius="16px", padding="24px",
                  box_shadow="0 8px 32px rgba(0,0,0,0.3)", **props)


def gradient_heading(text, size="3xl"):
    return rx.heading(text, size=size, weight="bold",
                      background_image=GRADIENT_TEXT, background_clip="text",
                      color="transparent", css={"-webkit-background-clip": "text"})


def status_dot(status):
    colors = {"idle": "#64748b", "running": "#22c55e", "error": "#ef4444"}
    return rx.box(width="10px", height="10px", border_radius="50%",
                  background=colors.get(status, "#64748b"),
                  css={"animation": "pulse 2s infinite" if status == "running" else "none"})


def step_ai_keys():
    return rx.vstack(
        gradient_heading("AI Provider Keys", "2xl"),
        rx.text("Connect your AI providers for content generation.", color=TEXT_SECONDARY),
        rx.spacer(height="16px"),
        rx.input(placeholder="GenX API Key", type="password", value=AppState.genx_api_key,
                 on_change=AppState.set_genx_api_key, background="rgba(15,23,42,0.8)",
                 border=GLASS_BORDER, color=TEXT_PRIMARY, padding="12px 16px",
                 border_radius="8px", width="100%"),
        rx.input(placeholder="DeepInfra API Key", type="password", value=AppState.deepinfra_api_key,
                 on_change=AppState.set_deepinfra_api_key, background="rgba(15,23,42,0.8)",
                 border=GLASS_BORDER, color=TEXT_PRIMARY, padding="12px 16px",
                 border_radius="8px", width="100%"),
        rx.input(placeholder="Together AI API Key", type="password", value=AppState.together_api_key,
                 on_change=AppState.set_together_api_key, background="rgba(15,23,42,0.8)",
                 border=GLASS_BORDER, color=TEXT_PRIMARY, padding="12px 16px",
                 border_radius="8px", width="100%"),
        spacing="12px", width="100%")


def step_social():
    platforms = [("Facebook", "facebook_connected"), ("Instagram", "instagram_connected"),
                 ("TikTok", "tiktok_connected"), ("LinkedIn", "linkedin_connected"),
                 ("X (Twitter)", "twitter_connected"), ("YouTube", "youtube_connected")]
    return rx.vstack(
        gradient_heading("Social Media Accounts", "2xl"),
        rx.text("Connect platforms for autonomous posting.", color=TEXT_SECONDARY),
        rx.spacer(height="16px"),
        *[rx.flex(
            rx.hstack(status_dot("running" if getattr(AppState, c) else "idle"),
                      rx.text(n, color=TEXT_PRIMARY)),
            rx.button("Connected" if getattr(AppState, c) else "Connect",
                      variant="solid" if getattr(AppState, c) else "outline",
                      color_scheme="green" if getattr(AppState, c) else "blue",
                      size="sm", border_radius="8px"),
            justify="between", align="center", width="100%", padding="12px 16px",
            background="rgba(15,23,42,0.5)", border_radius="8px", border=GLASS_BORDER
        ) for n, c in platforms],
        spacing="8px", width="100%")


def step_billing():
    return rx.vstack(
        gradient_heading("Billing & Notifications", "2xl"),
        rx.text("Configure payment and email services.", color=TEXT_SECONDARY),
        rx.spacer(height="16px"),
        rx.box(
            rx.hstack(rx.text("PayFast (ZAR)", weight="bold", color=ACCENT),
                      rx.badge("Ready to Activate", color_scheme="cyan", size="sm")),
            rx.spacer(height="8px"),
            rx.input(placeholder="Merchant ID", value=AppState.payfast_merchant_id,
                     on_change=AppState.set_payfast_merchant_id, background="rgba(15,23,42,0.8)",
                     border=GLASS_BORDER, color=TEXT_PRIMARY, padding="10px 14px",
                     border_radius="8px", width="100%"),
            rx.input(placeholder="Merchant Key", type="password", value=AppState.payfast_merchant_key,
                     on_change=AppState.set_payfast_merchant_key, background="rgba(15,23,42,0.8)",
                     border=GLASS_BORDER, color=TEXT_PRIMARY, padding="10px 14px",
                     border_radius="8px", width="100%"),
            rx.input(placeholder="Passphrase", type="password", value=AppState.payfast_passphrase,
                     on_change=AppState.set_payfast_passphrase, background="rgba(15,23,42,0.8)",
                     border=GLASS_BORDER, color=TEXT_PRIMARY, padding="10px 14px",
                     border_radius="8px", width="100%"),
            rx.checkbox("Sandbox Mode", checked=AppState.payfast_sandbox,
                        on_change=AppState.set_payfast_sandbox, color=TEXT_SECONDARY),
            padding="16px", background="rgba(6,182,212,0.05)", border_radius="12px",
            border="1px solid rgba(6,182,212,0.2)", width="100%", spacing="8px"),
        rx.spacer(height="12px"),
        rx.box(
            rx.hstack(rx.text("Email (Resend)", weight="bold", color=VIOLET),
                      rx.badge("Ready to Activate", color_scheme="violet", size="sm")),
            rx.spacer(height="8px"),
            rx.input(placeholder="Resend API Key (re_...)", type="password",
                     value=AppState.resend_api_key, on_change=AppState.set_resend_api_key,
                     background="rgba(15,23,42,0.8)", border=GLASS_BORDER,
                     color=TEXT_PRIMARY, padding="10px 14px", border_radius="8px", width="100%"),
            padding="16px", background="rgba(139,92,246,0.05)", border_radius="12px",
            border="1px solid rgba(139,92,246,0.2)", width="100%", spacing="8px"),
        spacing="12px", width="100%")


def step_brand():
    return rx.vstack(
        gradient_heading("Brand & Finish", "2xl"),
        rx.text("Customize your workspace.", color=TEXT_SECONDARY),
        rx.spacer(height="16px"),
        rx.input(placeholder="Brand Name", value=AppState.brand_name,
                 on_change=AppState.set_brand_name, background="rgba(15,23,42,0.8)",
                 border=GLASS_BORDER, color=TEXT_PRIMARY, padding="12px 16px",
                 border_radius="8px", width="100%"),
        rx.hstack(rx.color_picker(value=AppState.primary_color,
                                  on_change=AppState.set_primary_color),
                  rx.text("Primary Color", color=TEXT_SECONDARY), spacing="12px"),
        rx.hstack(rx.color_picker(value=AppState.accent_color,
                                  on_change=AppState.set_accent_color),
                  rx.text("Accent Color", color=TEXT_SECONDARY), spacing="12px"),
        rx.spacer(height="24px"),
        rx.button("Launch AMarkTAI Studio", size="lg", width="100%",
                  background=GRADIENT_TEXT, color="white", border_radius="12px",
                  padding="16px", font_weight="bold", font_size="18px",
                  on_click=AppState.complete_setup,
                  css={"transition": "transform 0.2s", "&:hover": {"transform": "scale(1.02)"}}),
        spacing="12px", width="100%")


def setup_wizard():
    steps = [step_ai_keys, step_social, step_billing, step_brand]
    labels = ["AI Providers", "Social Media", "Billing & Email", "Brand"]
    return rx.center(
        animated_bg(),
        rx.vstack(
            rx.hstack(
                rx.box(width="40px", height="40px", border_radius="10px", background=GRADIENT_TEXT,
                       display="flex", align_items="center", justify_content="center",
                       children=[rx.text("A", color="white", weight="bold", size="xl")]),
                gradient_heading("AMarkTAI Setup", "2xl"), align="center", spacing="12px"),
            rx.flex(*[rx.box(flex="1", height="4px", border_radius="2px", margin_x="2px",
                             background=PRIMARY if i <= AppState.current_step else "rgba(148,163,184,0.2)",
                             css={"transition": "background 0.3s ease"}) for i in range(4)],
                    width="100%", display="flex"),
            rx.hstack(*[rx.text(l, size="xs", color=PRIMARY if i == AppState.current_step else TEXT_SECONDARY,
                                weight="bold" if i == AppState.current_step else "normal")
                        for i, l in enumerate(labels)], justify="between", width="100%"),
            glass_card(steps[AppState.current_step]()),
            rx.hstack(
                rx.button("Back", variant="ghost", color=TEXT_SECONDARY,
                          on_click=AppState.prev_step, disabled=AppState.current_step == 0),
                rx.button("Next", color_scheme="blue", border_radius="8px",
                          on_click=AppState.next_step, disabled=AppState.current_step == 3),
                justify="between", width="100%"),
            spacing="20px", width="100%", max_width="600px", padding="40px"),
        min_height="100vh", width="100%")


def campaign_dashboard():
    return rx.vstack(
        animated_bg(),
        rx.box(rx.hstack(
            rx.box(width="36px", height="36px", border_radius="8px", background=GRADIENT_TEXT,
                   display="flex", align_items="center", justify_content="center",
                   children=[rx.text("A", color="white", weight="bold")]),
            gradient_heading(AppState.brand_name, "xl"), rx.spacer(),
            rx.button("Settings", variant="ghost", color=TEXT_SECONDARY, size="sm"),
            align="center", width="100%", padding="0 24px"), padding="16px 0", width="100%"),
        rx.box(rx.vstack(
            rx.hstack(
                rx.input(placeholder="Enter website URL to generate marketing content...",
                         value=AppState.target_url, on_change=AppState.set_target_url,
                         background="rgba(15,23,42,0.8)", border=GLASS_BORDER, color=TEXT_PRIMARY,
                         padding="14px 20px", border_radius="12px", font_size="16px", flex="1"),
                rx.button("Generate", size="lg", border_radius="12px", background=GRADIENT_TEXT,
                          color="white", padding="14px 32px", font_weight="bold",
                          loading=AppState.is_generating, on_click=AppState.start_generation,
                          css={"&:hover": {"transform": "scale(1.02)", "transition": "0.2s"}}),
                width="100%", spacing="12px"),
            rx.flex(*[rx.hstack(status_dot(AppState.agent_statuses.get(a, "idle")),
                                rx.text(a.capitalize(), size="xs", color=TEXT_SECONDARY),
                                spacing="6px", padding="6px 12px", background="rgba(15,23,42,0.5)",
                                border_radius="20px", border=GLASS_BORDER)
                      for a in ["scraper", "author", "video", "music", "publisher"]],
                    wrap="wrap", gap="8px", width="100%"),
            rx.cond(AppState.generated_assets.length() > 0,
                rx.grid(*[glass_card(
                    rx.text(asset.get("type", "content"), size="sm", color=ACCENT, weight="bold"),
                    rx.text(str(asset.get("preview", asset))[:200], size="sm",
                            color=TEXT_SECONDARY, line_clamp="3"),
                    rx.spacer(height="8px"),
                    rx.button("View Full", size="xs", variant="outline",
                              color_scheme="blue", border_radius="6px"),
                    spacing="8px") for asset in AppState.generated_assets],
                    columns="3", gap="16px", width="100%"),
                rx.cond(AppState.is_generating,
                    rx.center(rx.vstack(rx.spinner(size="xl", color=PRIMARY),
                                        rx.text("Agents working...", color=TEXT_SECONDARY, size="sm"),
                                        spacing="12px", align="center"), padding="60px", width="100%"),
                    rx.center(rx.text("Enter a URL above to start generating content",
                                      color=TEXT_SECONDARY, size="sm"), padding="60px", width="100%"))),
            spacing="20px", width="100%", max_width="1200px", padding="0 24px"),
        width="100%", flex="1"), min_height="100vh", width="100%")


def index():
    return rx.cond(AppState.setup_complete, campaign_dashboard(), setup_wizard())


app = rx.App(theme=rx.theme(appearance="dark"))
app.add_page(index, route="/", title="AMarkTAI Studio")
