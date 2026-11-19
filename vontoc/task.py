from datetime import timedelta

import frappe
from frappe.utils import get_datetime, now_datetime

from mail.client.doctype.push_subscription.push_subscription import (
    fetch_push_subscriptions,
    renew_push_subscription,
)


def renew_jmap_push_subscriptions():
    """Renew JMAP push subscriptions expiring within the next 3 days."""

    logger = frappe.logger("jmap_push_renewal")

    now = now_datetime()
    renew_before = now + timedelta(days=3)

    users = frappe.get_all(
        "User Settings",
        filters={"username": ["!=", None]},
        pluck="user",
    )

    for user in sorted(set(users)):
        try:
            if not frappe.db.get_value("User", user, "enabled"):
                continue

            subscriptions = fetch_push_subscriptions(
                user,
                page=1,
                limit=500,
            )

            for subscription in subscriptions:
                sub_id = subscription["id"]
                expires_value = subscription.get("expires")

                if not expires_value:
                    logger.warning(
                        f"JMAP Push subscription has no expiry: "
                        f"user={user}, id={sub_id}"
                    )
                    continue

                expires = get_datetime(expires_value)

                # Already expired: do not blindly recreate.
                if expires <= now:
                    logger.warning(
                        f"JMAP Push subscription already expired: "
                        f"user={user}, id={sub_id}, expires={expires}"
                    )
                    continue

                # Still has more than 3 days: no action needed.
                if expires > renew_before:
                    continue

                old_expires = expires

                # Renew using the existing Frappe Mail implementation.
                renew_push_subscription(user, sub_id)

                # Query Stalwart again to verify the new expiry.
                refreshed = fetch_push_subscriptions(
                    user,
                    page=1,
                    limit=500,
                )

                renewed = next(
                    (s for s in refreshed if s["id"] == sub_id),
                    None,
                )

                if not renewed or not renewed.get("expires"):
                    logger.error(
                        f"JMAP Push renewal could not be verified: "
                        f"user={user}, id={sub_id}"
                    )
                    continue

                new_expires = get_datetime(renewed["expires"])

                if new_expires > old_expires:
                    logger.info(
                        f"JMAP Push subscription renewed: "
                        f"user={user}, id={sub_id}, "
                        f"old={old_expires}, new={new_expires}"
                    )
                else:
                    logger.error(
                        f"JMAP Push expiry did not extend: "
                        f"user={user}, id={sub_id}, "
                        f"old={old_expires}, new={new_expires}"
                    )

        except Exception:
            logger.exception(
                f"Failed to maintain JMAP Push subscriptions for {user}"
            )