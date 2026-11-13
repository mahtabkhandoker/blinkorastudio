"""Customer-facing wording that is not a question: shot descriptions for
C1 (spec §2.7), notices and status messages. Bengali comes from the spec;
the English lines are translations of it.

The English generation prompt is never shown to a customer. These lines
are what the customer reads instead.
"""

from __future__ import annotations

# template id -> (bn, en). {detail} and {item} are filled per order.
SHOT_LINES: dict[str, tuple[str, str]] = {
    "G1-A": ("কাপড় হালকা বাতাসে দুলছে", "The fabric moves in a light breeze"),
    "G1-B": ("{detail}-এর ক্লোজ-আপ", "A close-up of {detail}"),
    "G1-C": ("ঝুলছে, ক্যামেরা পিছিয়ে যাচ্ছে", "It hangs still while the camera pulls back"),
    "G2-A": ("{item} ধীরে ঘুরছে", "The {item} turns slowly"),
    "G2-B": ("লেবেলের ক্লোজ-আপ", "A close-up of the label"),
    "G2-C": ("টেবিলে রাখা, ক্যামেরা পিছিয়ে", "On the table, with the camera pulling back"),
    "G3-A": ("আলো {item_gen} উপর দিয়ে যাচ্ছে", "Light travels across the {item}"),
    "G3-B": ("{detail}-এর ক্লোজ-আপ", "A close-up of {detail}"),
    "G3-C": ("ক্যামেরা পিছিয়ে পুরোটা", "The camera pulls back to show all of it"),
    "G4-A": ("কৌটা স্থির, আলো পড়ছে", "The container stays still as light falls on it"),
    "G4-B": ("ঢালার ক্লোজ-আপ", "A close-up of the pour"),
    "G4-B:wider": ("ঢালার দৃশ্য, একটু দূর থেকে", "The pour, from a little further back"),
    "G4-C": ("কৌটা টেবিলে, ক্যামেরা পিছিয়ে", "The container on the table, camera pulling back"),
    "G5-A": ("পানির ফোঁটা চিকচিক করছে", "Water droplets glisten on it"),
    "G5-A-DRY": ("আলো ধীরে সরে যাচ্ছে, একদম শুকনো", "Light moves slowly across it, completely dry"),
    "G5-B": ("গায়ের ক্লোজ-আপ", "A close-up of the surface"),
    "G5-C": ("পুরো ঝুড়ি দেখা যাচ্ছে", "The whole tray comes into view"),
    "S1": ("রুম {n}: ক্যামেরা ধীরে ভেতরে যাচ্ছে", "Room {n}: the camera moves slowly inside"),
    "S2": ("কাজের ফলাফল স্থির, ক্যামেরা ধীরে কাছে যাচ্ছে", "The finished result, with the camera moving slowly closer"),
    "S3-A": ("সরঞ্জামের ক্লোজ-আপ", "A close-up of the tools"),
    "S3-B": ("কাজ করা হাত", "Hands at work"),
    "S3-C": ("পুরো দোকান, ক্যামেরা ধীরে কাছে", "The whole shop, camera moving slowly closer"),
    "S4": (
        "আপনার পোস্টারের উপর ধীরে জুম — নতুন ভিডিও বানানো হবে না",
        "A slow zoom over your own poster — no new video is generated",
    ),
}

# Bengali/English wording for the default DETAIL of each group (C1 only).
DETAIL_LABEL: dict[str, tuple[str, str]] = {
    "G1": ("বুনন ও পাড়", "the weave and border"),
    "G3": ("গায়ের কারুকাজ", "the surface finish"),
}

POST_PRODUCTION_NOTE = (
    "নাম, নাম্বার আর দাম ভিডিওর উপরে বসানো হবে — ভিডিওর ভেতরে না।",
    "Your name, number and price are added on top of the video afterwards, not generated inside it.",
)

PLAN_INTRO = ("{n}টি দৃশ্য বানাব:", "We will make {n} scene(s):")
PLAN_INTRO_NO_GENERATION = ("এই অর্ডারে নতুন ভিডিও বানানো হবে না:", "No new video is generated for this order:")
PLAN_CLOSING = ("ঠিক আছে?", "Does this look right?")
CONFIRM_LABEL = ("হ্যাঁ, বানান", "Yes, make it")
CHANGE_LABEL = ("বদলাতে চাই", "I want changes")
CHANGE_NOTE_PREFIX = ("আপনার অনুরোধ: ", "Your request: ")

PHOTO_MESSAGES: dict[str, tuple[str, str]] = {
    "initial": ("পণ্যের একটা ছবি দিন।", "Send a photo of your product."),
    "more_photos": (
        "প্রতিটা রুমের জন্য একটা করে ছবি লাগবে। আরও {k}টি ছবি দিন।",
        "We need one photo per room. Please add {k} more photo(s).",
    ),
}

ASSET_WARNINGS: dict[str, tuple[str, str]] = {
    "BLURRY": ("ছবিটা একটু ঝাপসা।", "The photo is a little blurry."),
    "LOW_RESOLUTION": ("ছবিটা ছোট, তাই ভিডিও ঝাপসা হতে পারে।", "The photo is small, so the video may look soft."),
    "TOO_DARK": ("ছবিটা একটু অন্ধকার।", "The photo is a little dark."),
    "CROPPED": ("পণ্যের কিছু অংশ ছবির বাইরে চলে গেছে মনে হচ্ছে।", "Part of the product seems to be outside the frame."),
}
ASSET_OK = ("ছবিটা ভালো আছে।", "The photo looks good.")

UPLOAD_ERRORS: dict[str, tuple[str, str]] = {
    "FILE_TOO_LARGE": ("ছবিটা অনেক বড়। {mb} MB-এর ছোট ছবি দিন।", "The file is too large. Use an image under {mb} MB."),
    "EMPTY_FILE": ("ফাইলটা খালি।", "The file is empty."),
    "UNSUPPORTED_IMAGE": ("এই ধরনের ফাইল চলবে না। JPG, PNG বা WebP ছবি দিন।", "This file type isn't supported. Use a JPG, PNG or WebP image."),
    "CORRUPT_IMAGE": ("ছবিটা খোলা যাচ্ছে না। অন্য একটা ছবি দিন।", "The image can't be opened. Please send a different one."),
    "IMAGE_TOO_MANY_PIXELS": ("ছবিটার মাপ অনেক বড়। ছোট করে দিন।", "The image dimensions are too large. Please send a smaller one."),
}

GENERATION_MESSAGES: dict[str, tuple[str, str]] = {
    "QUEUED": ("পরীক্ষামূলক অর্ডার জমা হয়েছে।", "Test order submitted."),
    "RUNNING": ("পরীক্ষামূলক রান চলছে…", "Test run in progress…"),
    "SUCCEEDED": (
        "পরীক্ষামূলক রান শেষ। এটা পরীক্ষা ছিল — আসল ভিডিও তৈরি হয়নি।",
        "Test run finished. This was a simulation — no real video was produced.",
    ),
    "FAILED": ("পরীক্ষামূলক রান ব্যর্থ হয়েছে।", "The test run failed."),
}

ENVIRONMENT_NOTICE = (
    "পরীক্ষামূলক সংস্করণ: আসল ভিডিও তৈরি হয় না, কোনো টাকা কাটা হয় না।",
    "Pilot build: no real video is generated and nothing is charged.",
)

ELIGIBILITY_MESSAGES: dict[str, tuple[str, str]] = {
    "plan_ready": ("প্ল্যান তৈরি আছে", "The plan is ready"),
    "photo_ready": ("ব্যবহারযোগ্য ছবি আছে", "A usable photo is on file"),
    "not_submitted": ("এই অর্ডার আগে জমা হয়নি", "This order has not been submitted before"),
    "provider_safe": ("পরীক্ষামূলক (বিনামূল্যের) জেনারেটর চালু", "The simulated (free) generator is active"),
}


def pick(pair: tuple[str, str], locale: str) -> str:
    return pair[0] if locale == "bn" else pair[1]


def asset_warning_text(code: str | None, locale: str) -> str:
    if code is None:
        return pick(ASSET_OK, locale)
    return pick(ASSET_WARNINGS.get(code, ("ছবিতে একটু সমস্যা আছে।", "There is an issue with the photo.")), locale)
