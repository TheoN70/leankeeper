"""
LeanKeeper — Zulip extractor.

Extracts messages, channels and topics from Lean Zulip.
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
        """GET request to the Zulip API."""
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
        """Extract public channels (streams)."""
        logger.info("Extracting Zulip channels...")

        data = self._get("streams")
        streams = data.get("streams", [])

        count = 0
        with self.session_factory() as session:
            for stream in streams:
                name = stream["name"]
                # Filter on channels of interest
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

        logger.info(f"Channels: {count} extracted")
        return count

    # ──────────────────────────────────────────
    # Messages
    # ──────────────────────────────────────────

    def extract_messages(self, channel_name: str, update_only: bool = False):
        """
        Extract all messages from a channel.
        Uses anchor to paginate backward from the most recent message.
        In update mode, stops when hitting messages already in the database.
        """
        logger.info(f"Extracting messages from #{channel_name}...")

        # Get channel ID
        with self.session_factory() as session:
            channel = session.query(ZulipChannel).filter_by(name=channel_name).first()
            if not channel:
                logger.warning(f"Channel #{channel_name} not found in database. Run extract_channels() first.")
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
                    "apply_markdown": "false",  # We want raw markdown
                })
            except Exception as e:
                logger.error(f"Error extracting #{channel_name}: {e}")
                break

            messages = data.get("messages", [])
            if not messages:
                break

            # Detect duplicates (end of pagination)
            new_messages = [m for m in messages if m["id"] not in seen_ids]
            if not new_messages:
                break

            for m in new_messages:
                seen_ids.add(m["id"])

            already_exists_count = 0
            with self.session_factory() as session:
                for m in new_messages:
                    msg_id = m["id"]
                    if session.get(ZulipMessage, msg_id):
                        already_exists_count += 1
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

            logger.info(f"#{channel_name}: {total_count} messages extracted")

            # In update mode, stop when most messages in the batch already exist
            if update_only and already_exists_count > len(new_messages) // 2:
                logger.info(f"Update mode: reached existing messages in #{channel_name}, stopping")
                break

            # Backward pagination
            oldest_id = min(m["id"] for m in new_messages)
            anchor = str(oldest_id)

            time.sleep(1)  # Zulip rate limiting courtesy

        logger.info(f"#{channel_name} done: {total_count} messages")
        return total_count

    # ──────────────────────────────────────────
    # Orchestrator
    # ──────────────────────────────────────────

    def extract_all(self, update_only: bool = False):
        """Extract channels then all messages from configured channels."""
        self.extract_channels()

        total = 0
        for channel_name in ZULIP_CHANNELS:
            count = self.extract_messages(channel_name, update_only=update_only)
            if count:
                total += count

        logger.info(f"Zulip extraction done: {total} messages total")
