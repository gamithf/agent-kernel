import base64
import logging
import os
import tempfile
import traceback
from typing import Optional

import httpx
import openai
from agentkernel.api import RESTRequestHandler
from agentkernel.core import AgentService, Config
from agentkernel.core.model import AgentRequestFile, AgentRequestText
from fastapi import APIRouter, HTTPException, Request


class VetraWhatsAppHandler(RESTRequestHandler):
    def __init__(self):
        self._log = logging.getLogger("vetra.whatsapp")
        self._whatsapp_agent = Config.get().whatsapp.agent if Config.get().whatsapp.agent != "" else None
        self._acknowledgement = Config.get().whatsapp.agent_acknowledgement if Config.get().whatsapp.agent_acknowledgement != "" else None
        self._verify_token = Config.get().whatsapp.verify_token
        self._access_token = Config.get().whatsapp.access_token
        self._app_secret = Config.get().whatsapp.app_secret
        self._phone_number_id = Config.get().whatsapp.phone_number_id
        self._api_version = Config.get().whatsapp.api_version or "v22.0"
        self._base_url = f"https://graph.facebook.com/{self._api_version}"
        self._max_file_size = Config.get().api.max_file_size
        if not all([self._access_token, self._phone_number_id, self._verify_token]):
            self._log.error("WhatsApp configuration is incomplete. Please set access_token, phone_number_id, and verify_token.")
            raise ValueError("Incomplete WhatsApp configuration.")

    def get_router(self) -> APIRouter:
        router = APIRouter()

        @router.get("/health")
        def health():
            return {"status": "ok", "service": "vetra"}

        @router.get("/whatsapp/webhook")
        async def verify_webhook(request: Request):
            mode = request.query_params.get("hub.mode")
            token = request.query_params.get("hub.verify_token")
            challenge = request.query_params.get("hub.challenge")
            if mode == "subscribe" and token == self._verify_token and challenge:
                self._log.info("Webhook verified successfully")
                return int(challenge)
            raise HTTPException(status_code=403, detail="Verification failed")

        @router.post("/whatsapp/webhook")
        async def handle_webhook(request: Request):
            if self._app_secret:
                signature = request.headers.get("x-hub-signature-256", "")
                body = await request.body()
                if not self._verify_signature(body, signature):
                    self._log.warning("Invalid request signature")
                    raise HTTPException(status_code=403, detail="Invalid signature")
            try:
                body = await request.json()
                if body.get("object") == "whatsapp_business_account":
                    for entry in body.get("entry", []):
                        for change in entry.get("changes", []):
                            value = change.get("value", {})
                            if "messages" in value:
                                for message in value["messages"]:
                                    await self._handle_message(message, value)
                            if "statuses" in value:
                                for status in value["statuses"]:
                                    self._log.debug(f"Status update: {status.get('status')}")
            except Exception as e:
                self._log.error(f"Error processing webhook: {e}\n{traceback.format_exc()}")
            return {"status": "ok"}

        return router

    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        import hashlib
        import hmac

        if not signature.startswith("sha256="):
            return False
        expected = hmac.new(self._app_secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature[7:])

    async def _handle_message(self, message: dict, value: dict):
        message_id = message.get("id")
        from_number = message.get("from")
        message_type = message.get("type")

        if not from_number or not message_id:
            self._log.warning("Message missing required fields (from/id)")
            return

        self._log.debug(f"Processing message {message_id} from {from_number} of type {message_type}")

        text = None
        requests = []

        if message_type == "text":
            text = message.get("text", {}).get("body")

        elif message_type == "interactive":
            interactive = message.get("interactive", {})
            if interactive.get("type") == "button_reply":
                text = interactive.get("button_reply", {}).get("title")
            elif interactive.get("type") == "list_reply":
                text = interactive.get("list_reply", {}).get("title")

        elif message_type == "audio":
            audio_info = message.get("audio", {})
            media_id = audio_info.get("id")
            if media_id:
                transcript = await self._transcribe_audio(media_id)
                if transcript:
                    text = f"[Transcribed voice note]: {transcript}"
                else:
                    text = "[Voice note: transcription unavailable]"
            else:
                text = "[Voice note: no media ID]"

        elif message_type == "voice":
            voice_info = message.get("voice", {})
            media_id = voice_info.get("id")
            if media_id:
                transcript = await self._transcribe_audio(media_id)
                if transcript:
                    text = f"[Transcribed voice note]: {transcript}"
                else:
                    text = "[Voice note: transcription unavailable]"
            else:
                text = "[Voice note: no media ID]"

        elif message_type == "image":
            image_info = message.get("image", {})
            caption = image_info.get("caption", "")
            text = caption if caption else "[Image received]"
            media_id = image_info.get("id")
            if media_id:
                media_size, media_mime_type = await self._get_media_info(media_id)
                if media_size and media_size <= self._max_file_size:
                    image_data = await self._download_media(media_id)
                    if image_data:
                        requests.append(
                            AgentRequestFile(
                                file_data=image_data,
                                name=f"image_{message_id}",
                                mime_type=media_mime_type or "image/jpeg",
                            )
                        )

        elif message_type == "document":
            doc_info = message.get("document", {})
            caption = doc_info.get("caption", "")
            filename = doc_info.get("filename", "document")
            text = caption if caption else f"[Document received: {filename}]"
            media_id = doc_info.get("id")
            if media_id:
                media_size, media_mime_type = await self._get_media_info(media_id)
                if media_size and media_size <= self._max_file_size:
                    file_data = await self._download_media(media_id)
                    if file_data:
                        requests.append(
                            AgentRequestFile(
                                file_data=file_data,
                                name=filename,
                                mime_type=media_mime_type or "application/octet-stream",
                            )
                        )

        else:
            self._log.warning(f"Unsupported message type: {message_type}")
            return

        if not text and not requests:
            return

        requests.insert(0, AgentRequestText(prompt=text or ""))

        session_id = from_number
        service = AgentService()

        try:
            if self._acknowledgement:
                await self._send_message(from_number, self._acknowledgement, message_id)

            service.select(session_id=session_id, name=self._whatsapp_agent)
            if not service.agent:
                await self._send_message(from_number, "Sorry, no agent is available.", message_id)
                return

            result = await service.run_multi(requests=requests)
            response_text = str(result)
            if not response_text.strip():
                response_text = "I've processed your request. Is there anything else I can help with?"

            await self._send_message(from_number, response_text, message_id)

        except Exception as e:
            self._log.error(f"Error handling message: {e}\n{traceback.format_exc()}")
            await self._send_message(from_number, "Sorry, there was an error processing your request.", message_id)

    async def _transcribe_audio(self, media_id: str) -> str:
        try:
            media_size, media_mime_type = await self._get_media_info(media_id)
            if media_size is None:
                self._log.warning(f"Could not get media info for {media_id}")
                return ""

            max_audio_size = 25 * 1024 * 1024
            if media_size > max_audio_size:
                self._log.warning(f"Audio file too large: {media_size} bytes")
                return ""

            audio_data_b64 = await self._download_media(media_id)
            if not audio_data_b64:
                return ""

            audio_bytes = base64.b64decode(audio_data_b64)

            ext = ".ogg"
            if media_mime_type:
                if "mpeg" in media_mime_type or "mp3" in media_mime_type:
                    ext = ".mp3"
                elif "wav" in media_mime_type:
                    ext = ".wav"
                elif "mp4" in media_mime_type:
                    ext = ".mp4"

            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                with open(tmp_path, "rb") as f:
                    client = openai.AsyncOpenAI()
                    transcript_obj = await client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                    )
                return transcript_obj.text
            finally:
                os.unlink(tmp_path)

        except Exception as e:
            self._log.exception(f"Audio transcription failed for {media_id}")
            return ""

    async def _send_message(self, to_number: str, text: str, reply_to_message_id: Optional[str] = None):
        url = f"{self._base_url}/{self._phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}

        max_chars = 4096
        chunks = [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

        async with httpx.AsyncClient() as client:
            for i, chunk in enumerate(chunks):
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to_number,
                    "type": "text",
                    "text": {"body": chunk},
                }
                if i == 0 and reply_to_message_id:
                    payload["context"] = {"message_id": reply_to_message_id}
                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                except Exception as e:
                    detail = ""
                    try:
                        detail = resp.text[:500]
                    except Exception:
                        pass
                    self._log.error(f"Failed to send message to {to_number}: {e} | body={detail}")

    async def _get_media_info(self, media_id: str):
        try:
            url = f"{self._base_url}/{media_id}"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                info = resp.json()
                file_size = info.get("file_size")
                mime_type = info.get("mime_type")
                if file_size is None:
                    return None, None
                return int(file_size), mime_type
        except Exception as e:
            self._log.error(f"Error getting media info for {media_id}: {e}")
            return None, None

    async def _download_media(self, media_id: str) -> Optional[str]:
        try:
            url = f"{self._base_url}/{media_id}"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                media_info = resp.json()
                media_url = media_info.get("url")
                if not media_url:
                    self._log.error(f"No URL found for media ID {media_id}")
                    return None
                media_resp = await client.get(media_url, headers=headers)
                media_resp.raise_for_status()
                return base64.b64encode(media_resp.content).decode("utf-8")
        except Exception as e:
            self._log.error(f"Error downloading media {media_id}: {e}")
            return None
