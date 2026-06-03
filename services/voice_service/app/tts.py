import asyncio
import edge_tts

VOICE = "fr-FR-DeniseNeural"  # High-quality French neural voice (no install needed)

async def _speak_async(text: str, output_path: str, rate: str) -> None:
    communicate = edge_tts.Communicate(text, VOICE, rate=rate)
    await communicate.save(output_path)

def speak(text: str, output_path: str = "output.mp3", speed: float = 1.0) -> str:
    # Convert speed multiplier → edge-tts rate string
    # 1.0 → "+0%", 1.5 → "+50%", 0.8 → "-20%"
    rate_pct = int((speed - 1.0) * 100)
    rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"
    asyncio.run(_speak_async(text, output_path, rate_str))
    return output_path
