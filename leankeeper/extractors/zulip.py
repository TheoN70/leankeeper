"""
LeanKeeper — Extracteur Zulip.

Extrait les messages, channels et topics depuis le Zulip Lean.
Deux modes : API directe (nécessite un compte) ou archive HTML publique.
"""

import logging
import time
from datetime import datetime, timezone

import requests

from leankeeper.config import (
    BATCH_SIZE,
    ZULIP_API_KEY,
    ZULIP_BASE_URL,
    ZULIP_CHANNELS,
    ZULIP_EMAIL,
)
from leankeeper.models.database import ZulipChannel, ZulipMessage

logger = logging.getLogger(__name__)


class ZulipExtractor:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.auth = (ZULIP_EMAIL, ZULIP_API_KEY)

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Requête GET sur l'API Zulip."""
        url = f"{ZULIP_BASE_URL}/{endpoint}"
        response = requests.get(url, auth=self.auth, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("result") != "success":
            raise RuntimeError(f"Zulip API error: {data}")
        return data

    # ──────────────────────────────────────────
    # Channels (streams)
    # ──────────────────────────────────────────

    def extract_channels(self):
        """Extrait les channels (streams) publics."""
        logger.info("Extraction des channels Zulip...")

        data = self._get("streams")
        streams = data.get("streams", [])

        count = 0
        with self.session_factory() as session:
            for stream in streams:
                name = stream["name"]
                # Filtrer sur les channels d'intérêt
                if ZULIP_CHANNELS and name not in ZULIP_CHANNELS:
                    continue

                channel_id = stream["stream_id"]
                if session.get(ZulipChannel, channel_id):
                    continue

                session.add(ZulipChannel(
                    id=channel_id,
                    name=name,
                    description=stream.get("description", ""),
                ))
                count += 1

            session.commit()

        logger.info(f"Channels: {count} extraits")
        return count

    # ──────────────────────────────────────────
    # Messages
    # ──────────────────────────────────────────

    def extract_messages(self, channel_name: str):
        """
        Extrait tous les messages d'un channel.
        Utilise l'ancre pour paginer en arrière depuis le message le plus récent.
        """
        logger.info(f"Extraction des messages de #{channel_name}...")

        # Récupérer l'ID du channel
        with self.session_factory() as session:
            channel = session.query(ZulipChannel).filter_by(name=channel_name).first()
            if not channel:
                logger.warning(f"Channel #{channel_name} non trouvé en base. Lancer extract_channels() d'abord.")
                return
            channel_id = channel.id

        anchor = "newest"
        total_count = 0
        seen_ids = set()

        while True:
            try:
                data = self._get("messages", params={
                    "anchor": anchor,
                    "num_before": 1000,
                    "num_after": 0,
                    "narrow": f'[{{"operator": "stream", "operand": "{channel_name}"}}]',
                    "apply_markdown": "false",  # On veut le markdown brut
                })
            except Exception as e:
                logger.error(f"Erreur extraction #{channel_name}: {e}")
                break

            messages = data.get("messages", [])
            if not messages:
                break

            # Détecter les doublons (fin de pagination)
            new_messages = [m for m in messages if m["id"] not in seen_ids]
            if not new_messages:
                break

            for m in new_messages:
                seen_ids.add(m["id"])

            with self.session_factory() as session:
                for m in new_messages:
                    msg_id = m["id"]
                    if session.get(ZulipMessage, msg_id):
                        continue

                    session.add(ZulipMessage(
                        id=msg_id,
                        channel_id=channel_id,
                        topic=m.get("subject", ""),
                        sender_name=m.get("sender_full_name", ""),
                        sender_email=m.get("sender_email", ""),
                        content=m.get("content", ""),
                        timestamp=datetime.fromtimestamp(m["timestamp"], tz=timezone.utc),
                    ))
                    total_count += 1

                session.commit()

            logger.info(f"#{channel_name}: {total_count} messages extraits")

            # Pagination en arrière
            oldest_id = min(m["id"] for m in new_messages)
            anchor = str(oldest_id)

            time.sleep(1)  # Politesse Zulip

        logger.info(f"#{channel_name} terminé: {total_count} messages")
        return total_count

    # ──────────────────────────────────────────
    # Orchestrateur
    # ──────────────────────────────────────────

    def extract_all(self):
        """Extrait les channels puis tous les messages des channels configurés."""
        self.extract_channels()

        total = 0
        for channel_name in ZULIP_CHANNELS:
            count = self.extract_messages(channel_name)
            if count:
                total += count

        logger.info(f"Extraction Zulip terminée: {total} messages au total")
