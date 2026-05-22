from __future__ import annotations

import re
from typing import Any

from .config import Settings
from .models import CallbackQuery, IncomingMessage
from .permissions import PermissionContext, controller_num
from .redis_store import RedisStore
from .telegram import TelegramBot
from .texts import deny
from .ported_registry import ported_command_names


def reply_keyboard(rows: list[list[str]]) -> dict[str, Any]:
    return {
        "keyboard": [[{"text": text} for text in row] for row in rows],
        "resize_keyboard": True,
        "selective": True,
    }


def inline_keyboard(rows: list[list[tuple[str, str]]]) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": text, "callback_data": callback_data} for text, callback_data in row]
            for row in rows
        ]
    }


def inline_url(rows: list[list[dict[str, str]]]) -> dict[str, Any]:
    return {"inline_keyboard": rows}


DEVELOPER_HOME = [
    ["★ السـورس ★", "★ البـوت ★"],
    ["★ التواصــل ★"],
    ["★ الاشتـراك الاجبـاري ★"],
    ["★ الاذاعـه ★", "★ الاحصائيـات ★"],
    ["★ المطوريـن ★", "★ الـردود العـامـه ★"],
    ["★ الحظـر والكتـم العـام ★"],
    ["★ كاشـف الانتحـال ★"],
    ["★ تخصيص رتب البـوت ★"],
    ["★ قـروب اشعـارات البـوت ★"],
    ["★ كيبـورد الخـدمـات ★"],
]

SERVICES_HOME = [
    ["★ متحركـات ★", "★ افتـارات ★"],
    ["★ االذكـاء الاصطنـاعـي ★"],
    ["★ ميـوزك المكالمـات ★"],
    ["★ 𝗬𝗼𝘂𝗧𝘂𝗯𝗲🎞اليوتيوب ★"],
    ["★ العـاب ممطروقـه ★"],
    ["★ حالات واتس ★", "★ ترفيه ومرح ★"],
    ["★ سينما ومسرح ★"],
    ["★ اشعار واقتباسات ★", "★ قرآن كريم ★"],
    ["★ الطقـس ودرجة الحرارة ★"],
]

DEVELOPER_SECTIONS: dict[str, tuple[str, list[list[str]]]] = {
    "★ المطوريـن ★": (
        "*⇜ اليك الازرار الخاصـه بالمطـوريـن*",
        [
            ["✦ المطـور ✦"],
            ["✦ اوامـر المطـور الاسـاسـي ✦"],
            ["✦ المطورين الثانويين ✦", "✦ المطورات الثانويات ✦"],
            ["✦ المطـوريـن ✦", "✦ المطـورات ✦"],
            ["✦ تنزيل مطور اساسي ✦", "✦ رفع مطور اساسي ✦"],
            ["✦ تغيير كليشة المطور ✦", "✦ حذف كليشة المطور ✦"],
            ["✦ الغـاء الامــر ✦"],
            ["✦ رجـوع ✦"],
        ],
    ),
    "★ البـوت ★": (
        "*⇜ اليك الازرار الخاصـه بـ اوامـر البـوت*",
        [
            ["✦ تغيير اسم البوت ✦", "✦ حذف اسم البوت ✦"],
            ["✦ تعيين نـوع البوت ✦"],
            ["✦ تفعيل البوت الخدمي ✦"],
            ["✦ تعطيل البوت الخدمي ✦"],
            ["✦ تعطيل نداء المطور ✦", "✦ تفعيل نداء المطور ✦"],
            ["✦ الغـاء الامــر ✦"],
            ["✦ رجـوع ✦"],
        ],
    ),
    "★ الاحصائيـات ★": (
        "*⇜ اليك الازرار الخاصه بقسـم إحصـائيات البـوت*",
        [
            ["✦ الاحصـائيـات ✦"],
            ["✦ ترند المجموعات ✦", "✦ روابط المجموعات ✦"],
            ["✦ تنظيف المجموعات ✦", "✦ تنظيف المشتركين ✦"],
            ["✦ جلب نسخه احتياطيه ✦"],
            ["✦ جلب نسخة الردود ✦"],
            ["✦ جلب نسخه الردود عام ✦"],
            ["✦ تفعيل نسخه تلقائيه ✦", "✦ تعطيل نسخه تلقائيه ✦"],
            ["✦ رجـوع ✦"],
        ],
    ),
    "★ الـردود العـامـه ★": (
        "*⇜ اليك الازرار الخاصه بقسـم ردود البـوت عـام*",
        [
            ["اضف رد عام", "اضف رد متعدد عام"],
            ["مسح رد عام", "مسح رد متعدد عام"],
            ["الردود العامه", "الردود المتعدده عام"],
            ["الغاء الامر"],
            ["✦ رجـوع ✦"],
        ],
    ),
    "★ الاذاعـه ★": (
        "*⇜ اليك الازرار الخاصـه بالاذاعـه*",
        [
            ["✦ اذاعـه بالتثبيت ✦"],
            ["✦ اذاعـه للمجموعـات ✦", "✦ اذاعـه خـاص ✦"],
            ["✦ اذاعـه بالتوجيـه ✦", "✦ اذاعه بالتوجيه خاص ✦"],
            ["✦ الغـاء الامــر ✦"],
            ["✦ رجـوع ✦"],
        ],
    ),
    "★ الاشتـراك الاجبـاري ★": (
        "*⇜ اليك الازرار الخاصه بقسـم الاشتـراك الاجبـاري*",
        [
            ["ضع تاريخ الاشتراك", "اشتراك البوت"],
            ["الاشتراك الاجباري", "تغيير الاشتراك الاجباري"],
            ["تفعيل الاشتراك الاجباري", "تعطيل الاشتراك الاجباري"],
            ["الغاء الامر"],
            ["✦ رجـوع ✦"],
        ],
    ),
    "★ التواصــل ★": (
        "*⇜ اليك الازرار الخاصه بقسـم التواصـل*",
        [
            ["تعطيل التواصل", "تفعيل التواصل"],
            ["تعطيل ردود التواصل", "تفعيل ردود تواصل"],
            ["مسح رد تواصل", "اضف رد تواصل"],
            ["ردود التواصل"],
            ["الغاء الامر"],
            ["✦ رجـوع ✦"],
        ],
    ),
    "★ الحظـر والكتـم العـام ★": (
        "*⇜ اليك الازرار الخاصه بالكتـم والحظـر العـام*",
        [
            ["المحظورين عام", "المكتومين عام"],
            ["مسح المحظورين عام", "مسح المكتومين عام"],
            ["قائمه العام"],
            ["الغاء الامر"],
            ["✦ رجـوع ✦"],
        ],
    ),
    "★ كاشـف الانتحـال ★": (
        "*⇜ اليك اوامـر كاشف الانتحال 🥷*\n\n⇜ عند تفعيله يحاول البوت كشف من ينتحل اسم المطور وتنبيهه/كتمه حسب الاعداد.",
        [
            ["✦ تفعيل كاشف الانتحال ✦"],
            ["✦ تعطيل كاشف الانتحال ✦"],
            ["✦ الغـاء الامــر ✦"],
            ["✦ رجـوع ✦"],
        ],
    ),
    "★ تخصيص رتب البـوت ★": (
        "*⇜ اليك الازرار الخاصه بتخصيص وتغييـر رتب البـوت عـام*",
        [
            ["✦ رتبة المطور الاساسي ✦"],
            ["✦ رتبة المطور الاساسي2 ✦"],
            ["✦ رتبة المطور الثانوي ✦"],
            ["✦ رتبة المطوره الثانويه ✦"],
            ["✦ رتبة المطوره ✦", "✦ رتبة المطور ✦"],
            ["✦ رتبة المالك الاساسي ✦"],
            ["✦ رتبة المالكه الاساسيه ✦"],
            ["✦ رتبة المالكه ✦", "✦ رتبة المالك ✦"],
            ["✦ رتبة المنشئ الاساسي ✦"],
            ["✦ رتبة المنشئه الاساسيه ✦"],
            ["✦ رتبة المنشئه ✦", "✦ رتبة المنشئ ✦"],
            ["✦ رتبة المديره ✦", "✦ رتبة المدير ✦"],
            ["✦ رتبة الادمونه ✦", "✦ رتبة الادمن ✦"],
            ["✦ رتبة المميزه ✦", "✦ رتبة المميز ✦"],
            ["✦ رتبة العضو ✦"],
            ["✦ الغـاء الامــر ✦"],
            ["✦ رجـوع ✦"],
        ],
    ),
    "★ قـروب اشعـارات البـوت ★": (
        "*⇜ اليك اوامـر قـروب اشعـارات سجـل البـوت 🛎*",
        [
            ["✦ تفعيل قروب الاشعارات ✦"],
            ["✦ تعطيل قروب الاشعارات ✦"],
            ["✦ الغـاء الامــر ✦"],
            ["✦ رجـوع ✦"],
        ],
    ),
    "★ السـورس ★": (
        "*⇜ الازرار الخاصه*",
        [
            ["ضع صوره للترحيب", "معلومات التنصيب"],
            ["تعيين رمز السورس", "مسح رمز السورس"],
            ["تعيين قناة الحقوق", "مسح قناة الحقوق"],
            ["تغيير كليشه المطور", "مسح كليشه المطور"],
            ["تغيير كليشة السورس", "مسح كليشة السورس"],
            ["تنظيف المجموعات", "تنظيف المشتركين"],
            ["الغاء الامر"],
            ["✦ رجـوع ✦"],
        ],
    ),
}

SERVICE_SECTIONS: dict[str, tuple[str, list[list[str]]]] = {
    "★ اشعار واقتباسات ★": ("*⇜ في قسـم الاشعـار والاقتباسـات ⎋*", [["شعر", "قصائد"], ["لوكيت", "عبارات"], ["جداريات", "هيدرات"], ["اقتباسات", "اقتباس"], ["رجــوع"]]),
    "★ ترفيه ومرح ★": ("*⇜ في قسـم الترفيـه والمـرح ⎋*", [["مسلسل", "فلم"], ["ايدت انمي", "ايدت"], ["اطربني", "اغاني"], ["رجــوع"]]),
    "★ سينما ومسرح ★": ("*⇜ في قسـم السينمـا والمسـرح ⎋*", [["مسلسل", "فلم"], ["رجــوع"]]),
    "★ افتـارات ★": ("*⇜ في قسـم الافتـآرات والصـور ⎋*", [["افتارات تطقيم"], ["افتارات بنات", "افتارات عيال"], ["افتارات كيبوب", "افتارات انمي"], ["افتارات فنانين", "افتارات لاعبين"], ["رجــوع"]]),
    "★ متحركـات ★": ("*⇜ في قسـم المتحـركـات المتنـوعـه ⎋*", [["متحركات بنات", "متحركات عيال"], ["متحركات اطفال", "متحركات كيبوب"], ["متحركات كوكسال", "متحركات رومانسيه"], ["متحركات قطط"], ["رجــوع"]]),
    "★ االذكـاء الاصطنـاعـي ★": ("*『  الذكــاء الاصطنــاعــي 💡🦾  』*\n\n⇜ كل ماعليك هو فقط ارسال:\n`بوت` + سؤالك", [["رجــوع"]]),
    "★ ميـوزك المكالمـات ★": ("*『  الميـوزك & المكالمـات 🎶🎧 』*\n\n⇜ لتصفح اوامر قسم الميوزك ارسل: `ميوزك`", [["رجــوع"]]),
    "★ 𝗬𝗼𝘂𝗧𝘂𝗯𝗲🎞اليوتيوب ★": ("*『  اليوتيوب 🎞 𝗬𝗼𝘂𝗧𝘂𝗯𝗲  』*\n\n⇜ لتحميل الصوت ارسل `تحميل صوت` مع رابط يوتيوب\n⇜ لتحميل الفيديو ارسل `تحميل فيديو` مع رابط يوتيوب", [["رجــوع"]]),
    "★ العـاب ممطروقـه ★": ("*『  قائمـة الالعـاب الجديـدة 🎮🎳  』*\n\n⇜ مريم، الوان، سيارتي، والعاب الانلاين.", [["★ لعبـة مريـم ★"], ["★ شخصيتك من لونك المفضـل ★"], ["★ لعبـة سيارتـي ★"], ["★ العـاب الانـلايـن ★"], ["رجــوع"]]),
    "★ حالات واتس ★": ("*⇜ قسم حالات واتس*", [["حالات واتس", "حالات"], ["رجــوع"]]),
    "★ قرآن كريم ★": ("*⇜ قسم القرآن الكريم*", [["قران", "اذكار"], ["رجــوع"]]),
    "★ الطقـس ودرجة الحرارة ★": ("*⇜ لمعرفة الطقس ارسل:* `طقس بغداد`", [["رجــوع"]]),
}

HELP_PAGES: dict[str, str] = {
    "help1": "*『 اوامــر الادارة 💡🦾 』*\n\n• رفع/تنزيل مالك اساسي، مالك، منشئ اساسي، منشئ، مدير، ادمن، مميز\n• مسح الرتب والقوائم والردود والميديا\n• حظر، كتم، طرد، تقييد، رفع القيود",
    "help2": "*『 اوامــر القفـل والتعطيـل 💡🦾 』*\n\n• قفل/فتح الروابط، المعرفات، الصور، الفيديو، الملفات، البوتات، التوجيه، الاغاني، الجهات، السب، الاباحي، الدردشة\n• تفعيل/تعطيل الترحيب، الردود، الرفع، الايدي، البنك، الالعاب، الصوتيات",
    "help3": "*『 قوائــم القفــل / التعطيـل 』*\n\n• الاعدادات\n• اعدادات الحماية\n• الحمايه\n• ردود البوت",
    "help4": "*『 اوامــر الوضــع والاضـافـات 』*\n\n• الرابط، القوانين، الترحيب، الوصف، الادمنيه، المنشئين، المدراء، الادمنية، المميزين",
    "help5": "*『 اوامــر التسليـه والتحشيش 』*\n\n• غنيلي، انطق، كت، لو خيروك، صراحه، كرسي، عقاب، احكام، زواج، طلاق",
    "helpp6": "*『 اوامــر الخدمـات والتـرفيـه 』*\n\n• /cmds\n• يوتيوب، طقس، صلاة، زخرفة، صور، افتارات، متحركات، اقتباسات",
    "help7": "*『 اوامــر الالعــاب 』*\n\n• العاب، بنك، سمايلات، لغز، توب الالعاب، نقاطي",
    "help8": "*『 اوامــر الـــردود والهـمسـات 』*\n\n• اضف رد، مسح رد، الردود، اضف رد عام، مسح رد عام، همسه، اهمسلي، زاجل",
    "help9": "*『 اوامــر التـاك والمنشــن 』*\n\n• تاك، منشن، تاك للكل، تعطيل/تفعيل تاك عام",
    "hellp10": "*『 اوامــر التــوب تــرنـد 』*\n\n• توب التفاعل، توب الرسائل، اغنياء، ترتيبي، ترند المجموعات",
    "hellp11": "*『 اوامــر الحـمـاية الـذكـيــه 』*\n\n• كاشف الاباحي، كاشف الانتحال، الحماية، التفليش، الفارسيه، السب",
    "hellp12": "*『 اوامــر الذكــاء الاصطنــاعـي 』*\n\n• بوت + سؤالك\n• تحليل الصور والفيديو عند تفعيل NSFW",
    "hellp13": "*『 اوامــر الميـوزك فـي المكالمـات 』*\n\n• ميوزك\n• تشغيل، ايقاف، تخطي، تحميل صوت/فيديو من يوتيوب",
}

STATUS_CALLBACKS = {
    "Status_link": ("Zelzal:Lock:Link", "الروابط"),
    "Status_spam": ("Zelzal:Lock:Spam", "السبام"),
    "Status_keypord": ("Zelzal:Lock:Keyboard", "الكيبورد"),
    "Status_voice": ("Zelzal:Lock:vico", "الصوت"),
    "Status_gif": ("Zelzal:Lock:Animation", "المتحركات"),
    "Status_files": ("Zelzal:Lock:Document", "الملفات"),
    "Status_text": ("Zelzal:Lock:text", "الشات"),
    "Status_video": ("Zelzal:Lock:Video", "الفيديو"),
    "Status_photo": ("Zelzal:Lock:Photo", "الصور"),
    "Status_username": ("Zelzal:Lock:User:Name", "المعرفات"),
    "Status_tags": ("Zelzal:Lock:hashtak", "التاك"),
    "Status_bots": ("Zelzal:Lock:Bot:kick", "البوتات"),
    "Status_farsia": ("Zelzal:Lock:farsia", "الفارسيه"),
    "Status_tphlesh": ("Zelzal:Lock:tphlesh", "الحمايه"),
    "Status_alphsar": ("Zelzal:Lock:phshar", "السب"),
}

MUTE_CALLBACKS = {
    "mute_link": ("Zelzal:Status:Link", True, "الرابط"),
    "unmute_link": ("Zelzal:Status:Link", False, "الرابط"),
    "mute_welcome": ("Zelzal:Status:Welcome", True, "الترحيب"),
    "unmute_welcome": ("Zelzal:Status:Welcome", False, "الترحيب"),
    "mute_Id": ("Zelzal:Status:Id", True, "الايدي"),
    "unmute_Id": ("Zelzal:Status:Id", False, "الايدي"),
    "mute_IdPhoto": ("Zelzal:Status:IdPhoto", True, "الايدي بالصوره"),
    "unmute_IdPhoto": ("Zelzal:Status:IdPhoto", False, "الايدي بالصوره"),
    "mute_ryple": ("Zelzal:Status:Reply", True, "الردود"),
    "unmute_ryple": ("Zelzal:Status:Reply", False, "الردود"),
    "mute_ryplesudo": ("Zelzal:Status:ReplySudo", True, "الردود العامه"),
    "unmute_ryplesudo": ("Zelzal:Status:ReplySudo", False, "الردود العامه"),
    "mute_games": ("Zelzal:Status:Games", True, "الالعاب"),
    "unmute_games": ("Zelzal:Status:Games", False, "الالعاب"),
}


class MenuService:
    def __init__(self, settings: Settings, store: RedisStore, bot: TelegramBot) -> None:
        self.settings = settings
        self.store = store
        self.bot = bot
        self.known_commands = ported_command_names()

    async def handle(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        text = msg.effective_text or ""
        if text in {"/start", "start"} and msg.chat_type == "private":
            await self._start(msg, ctx)
            return True
        if text in {"✦ رجـوع ✦", "العوده"} and ctx.controller_bot:
            await self._developer_home(msg)
            return True
        if text in {"/cmds", "/keb", "★ كيبـورد الخـدمـات ★", "رجــوع"}:
            await self._services_home(msg, ctx)
            return True
        if text in {"اوامر المطور"}:
            text = "★ المطوريـن ★"
        if text in {"اوامر الردود"}:
            text = "★ الـردود العـامـه ★"
        if text in {"اوامر الاشتراك الاجباري"}:
            text = "★ الاشتـراك الاجبـاري ★"
        if text in {"اوامر التواصل"}:
            text = "★ التواصــل ★"
        if text in DEVELOPER_SECTIONS:
            if not ctx.controller_bot:
                await self.bot.send_message(msg.chat_id, deny(controller_num(1)), msg.message_id)
                return True
            label, rows = DEVELOPER_SECTIONS[text]
            await self.bot.send_message(msg.chat_id, label, msg.message_id, reply_markup=reply_keyboard(rows))
            return True
        if text in SERVICE_SECTIONS:
            label, rows = SERVICE_SECTIONS[text]
            await self.store.sadd(self.store.key("Zelzal:Num:User:Pv"), msg.user_id)
            await self.store.set(self.store.key("keyboardmemb", msg.user_id), "true")
            await self.bot.send_message(msg.chat_id, label, msg.message_id, reply_markup=reply_keyboard(rows))
            return True
        if text in {"الاوامر", "/Commands", f"/Commands@{self.settings.bot_username}"}:
            if not ctx.admin:
                await self.bot.send_message(msg.chat_id, "\n*⇜ متأكد انك مو عضو ؟!*\n*⇜ لان الامر خاص بالادمنيه واعلى😕*", msg.message_id)
                return True
            await self._group_commands(msg)
            return True
        if text in {"تقييم", "تقيم"}:
            await self._rating(msg)
            return True
        if text in {"الالعاب", "العاب"}:
            await self._games_menu(msg)
            return True
        if text in {"الحمايه", "الحماية"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self._protection_toggles(msg)
            return True
        if text in {"الاعدادات", "اعدادات القروب", "اعدادات الجروب", "اعدادات الكروب", "اعدادات المجموعة", "اعدادات المجموعه"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self._settings_inline(msg)
            return True
        if text in {"اعدادات الحمايه", "اعدادات الحماية"}:
            if not ctx.admin:
                await self.bot.send_message(msg.chat_id, deny(controller_num(7)), msg.message_id)
                return True
            await self._protection_status(msg)
            return True
        if text == "ردود البوت":
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self._bot_replies_panel(msg)
            return True
        return False

    async def handle_callback(self, callback: CallbackQuery) -> bool:
        data = callback.data or ""
        user_id, action = self._split_callback(data)
        if user_id and user_id != callback.user_id:
            await self.bot.answer_callback_query(callback.id, "• الامر لا يخصك", True)
            return True
        if action in {"helpall", "back", "Commands"}:
            if callback.chat_id and callback.message_id:
                try:
                    await self.bot.edit_message_text(
                        callback.chat_id,
                        callback.message_id,
                        self._group_commands_text(),
                        reply_markup=self._group_commands_markup(callback.user_id),
                    )
                except Exception:
                    # ignore Telegram editMessageText failures (stale message id / already edited / etc)
                    pass
            await self.bot.answer_callback_query(callback.id, "⇜ رجعت للقائمة الرئيسية", False)
            return True
        if action in HELP_PAGES:
            if callback.chat_id and callback.message_id:
                try:
                    await self.bot.edit_message_text(
                        callback.chat_id,
                        callback.message_id,
                        HELP_PAGES[action],
                        reply_markup=inline_keyboard([[("رجـوع", f"{callback.user_id}/helpall")]]),
                    )
                except Exception:
                    pass
            await self.bot.answer_callback_query(callback.id, "⇜ تم فتح القائمة", False)
            return True
        if action in STATUS_CALLBACKS and callback.chat_id:
            key, label = STATUS_CALLBACKS[action]
            redis_key = self.store.key(key, callback.chat_id)
            if await self.store.get(redis_key):
                await self.store.delete(redis_key)
                state = "فتح"
            else:
                await self.store.set(redis_key, "del")
                state = "قفل"
            await self.bot.answer_callback_query(callback.id, f"⇜ تم {state} {label}", True)
            return True
        if action in MUTE_CALLBACKS and callback.chat_id:
            key, enabled, label = MUTE_CALLBACKS[action]
            redis_key = self.store.key(key, callback.chat_id)
            if enabled:
                await self.store.set(redis_key, "true")
                state = "تفعيل"
            else:
                await self.store.delete(redis_key)
                state = "تعطيل"
            await self.bot.answer_callback_query(callback.id, f"⇜ تم {state} {label}", True)
            return True
        if action == "delAmr" and callback.chat_id and callback.message_id:
            try:
                await self.bot.delete_message(callback.chat_id, callback.message_id)
            except Exception:
                pass
            await self.bot.answer_callback_query(callback.id, "⇜ تم اخفاء الامر", False)
            return True
        if re.fullmatch(r"takeeem[1-5]", action):
            await self.store.incrby(self.store.key("Zilzal:Takeem:T", action[-1]), 1)
            await self.bot.answer_callback_query(callback.id, "⇜ شكراً لتقييمك", True)
            return True
        return False

    async def _start(self, msg: IncomingMessage, ctx: PermissionContext) -> None:
        await self.store.sadd(self.store.key("Zelzal:Num:User:Pv"), msg.user_id)
        bot_name = await self.store.get(self.store.key("Zelzal:Name:Bot")) or "البوت"
        custom = await self.store.get(self.store.key("Zelzal:Start:Bot"))
        if ctx.controller_bot:
            await self._developer_home(msg)
            return
        text = custom or (
            f"*⇜ اططلـق بـوت اسمـي {bot_name}\n"
            "⇜ بوت خدمي + حماية + ذكاء اصطناعي + زخرفة + همسه .. والمزيد\n"
            "⇜ فقط ارفعني إشراف كامل الصلاحيات وسيتم التفعيل تلقائياً\n\n"
            "⇜ لعرض كيبورد الاوامر الخدمية اضغط ← /cmds *"
        )
        username = self.settings.bot_username or "bot"
        markup = inline_url([[{"text": f"✦ إضغط لاضافه {bot_name} لمجموعتك ✦", "url": f"https://t.me/{username}?startgroup=new"}]])
        await self.bot.send_message(msg.chat_id, text, msg.message_id, reply_markup=markup)

    async def _developer_home(self, msg: IncomingMessage) -> None:
        await self.bot.send_message(
            msg.chat_id,
            "*⇜ مرحبـاً بـك مطـوري الغـالي🧑🏻‍💻\n⇜ في لوحتـك الخـاصـه لـ التحكـم بـ البـوت ⎋*",
            msg.message_id,
            reply_markup=reply_keyboard(DEVELOPER_HOME),
        )

    async def _services_home(self, msg: IncomingMessage, ctx: PermissionContext) -> None:
        rows = SERVICES_HOME + ([["✦ رجـوع ✦"]] if ctx.controller_bot else [])
        await self.store.sadd(self.store.key("Zelzal:Num:User:Pv"), msg.user_id)
        await self.store.set(self.store.key("keyboardmemb", msg.user_id), "true")
        await self.bot.send_message(
            msg.chat_id,
            "*⇜ مرحبـاً بـك عـزيـزي🧑🏻‍💻\n⇜ في لوحـة الاوامـر الخدميـه ⎋*",
            msg.message_id,
            reply_markup=reply_keyboard(rows),
        )

    async def _group_commands(self, msg: IncomingMessage) -> None:
        await self.bot.send_message(msg.chat_id, self._group_commands_text(), msg.message_id, reply_markup=self._group_commands_markup(msg.user_id))

    def _group_commands_text(self) -> str:
        return (
            "*⎙┊يـوجـد ← 𝟙𝟛 قـائمــة فـي البــوت\n"
            "ٴ⋆┄─┄─┄─┄┄─┄─┄─┄─┄┄⋆\n"
            " ⦇ ① ⦈ ← اوامــر الإدارة & الـرتب\n"
            " ⦇ ② ⦈ ← اوامــر القفـل والتعطيـل\n"
            " ⦇ ③ ⦈ ← قوائــم القفــل / التعطيـل\n"
            " ⦇ ④ ⦈ ← اوامــر الوضــع والاضـافـات\n"
            " ⦇ ⑤ ⦈ ← اوامــر التسليـه والتحشيش\n"
            " ⦇ ⑥ ⦈ ← اوامــر الخدمـات والتـرفيـه\n"
            " ⦇ ⑦ ⦈ ← اوامــر الالعــاب\n"
            " ⦇ ⑧ ⦈ ← اوامــر الـــردود والهـمسـات\n"
            " ⦇ ⑨ ⦈ ← اوامــر التـاك والمنشــن\n"
            " ⦇ ⑩ ⦈ ← اوامــر التــوب تــرنـد\n"
            " ⦇ ⑪ ⦈ ← اوامــر الحـمـاية الـذكـيــه\n"
            " ⦇ ⑫ ⦈ ← اوامــر الذكــاء الاصطنــاعـي\n"
            " ⦇ ⑬ ⦈ ← اوامــر الميـوزك فـي المكالمـات\n"
            "ٴ⋆┄─┄─┄─┄┄─┄─┄─┄─┄┄⋆\n"
            "⭐┊لـ تقييـم اداء البـوت ارسل ← تقييم*"
        )

    def _group_commands_markup(self, user_id: int) -> dict[str, Any]:
        return inline_keyboard([
            [("❶", f"{user_id}/help1"), ("❷", f"{user_id}/help2"), ("❸", f"{user_id}/help3"), ("❹", f"{user_id}/help4"), ("❺", f"{user_id}/help5")],
            [("❻", f"{user_id}/helpp6"), ("❼", f"{user_id}/help7"), ("❽", f"{user_id}/help8"), ("❾", f"{user_id}/help9"), ("❿", f"{user_id}/hellp10")],
            [("⓫", f"{user_id}/hellp11"), ("⓬", f"{user_id}/hellp12"), ("⓭", f"{user_id}/hellp13")],
        ])

    async def _rating(self, msg: IncomingMessage) -> None:
        values = [await self.store.get(self.store.key("Zilzal:Takeem:T", i)) or "0" for i in range(1, 6)]
        rows = [[("⭐" * i + f"⤑ {values[i - 1]}", f"/takeeem{i}")] for i in range(1, 6)]
        await self.bot.send_message(msg.chat_id, "*- مرحبـاً بك عـزيـزي 🫂*\n*- قم بـ تقييـم اداء البـوت*", msg.message_id, reply_markup=inline_keyboard(rows))

    async def _games_menu(self, msg: IncomingMessage) -> None:
        await self.bot.send_message(
            msg.chat_id,
            "*✦ قائمــة العــاب البــوت 🎳*\n\n✦ العاب الانلاين » بلاي\n✦ البنك » بنك\n✦ احكام، صراحه، كرسي، عقاب\n✦ مريم، الوان، اعلام، عواصم\n✦ لو خيروك، كت، سمايلات، لغز",
            msg.message_id,
            reply_markup=inline_keyboard([[("شروحـات الالعـاب", f"{msg.user_id}/gamesdes")], [("القائمه الرئيسية", f"{msg.user_id}/helpall")]]),
        )

    async def _protection_toggles(self, msg: IncomingMessage) -> None:
        rows = [
            [("تعطيل الرابط", f"{msg.user_id}/unmute_link"), ("تفعيل الرابط", f"{msg.user_id}/mute_link")],
            [("تعطيل الترحيب", f"{msg.user_id}/unmute_welcome"), ("تفعيل الترحيب", f"{msg.user_id}/mute_welcome")],
            [("تعطيل الايدي", f"{msg.user_id}/unmute_Id"), ("تفعيل الايدي", f"{msg.user_id}/mute_Id")],
            [("تعطيل الايدي بالصوره", f"{msg.user_id}/unmute_IdPhoto"), ("تفعيل الايدي بالصوره", f"{msg.user_id}/mute_IdPhoto")],
            [("تعطيل الردود", f"{msg.user_id}/unmute_ryple"), ("تفعيل الردود", f"{msg.user_id}/mute_ryple")],
            [("تعطيل الردود العامه", f"{msg.user_id}/unmute_ryplesudo"), ("تفعيل الردود العامه", f"{msg.user_id}/mute_ryplesudo")],
            [("تعطيل الالعاب", f"{msg.user_id}/unmute_games"), ("تفعيل الالعاب", f"{msg.user_id}/mute_games")],
            [("إخفـاء الامـر", f"{msg.user_id}/delAmr")],
        ]
        await self.bot.send_message(msg.chat_id, "⇜ اوامر التفعيل والتعطيل ", msg.message_id, reply_markup=inline_keyboard(rows))

    async def _settings_inline(self, msg: IncomingMessage) -> None:
        rows = [
            [(await self._lock_label("Zelzal:Lock:Link", msg.chat_id), f"{msg.user_id}/Status_link"), ("الروابط : ", f"{msg.user_id}/Status_link")],
            [(await self._lock_label("Zelzal:Lock:Spam", msg.chat_id), f"{msg.user_id}/Status_spam"), ("السبام : ", f"{msg.user_id}/Status_spam")],
            [(await self._lock_label("Zelzal:Lock:Photo", msg.chat_id), f"{msg.user_id}/Status_photo"), ("الصور : ", f"{msg.user_id}/Status_photo")],
            [(await self._lock_label("Zelzal:Lock:Video", msg.chat_id), f"{msg.user_id}/Status_video"), ("الفيديو : ", f"{msg.user_id}/Status_video")],
            [(await self._lock_label("Zelzal:Lock:User:Name", msg.chat_id), f"{msg.user_id}/Status_username"), ("المعرفات : ", f"{msg.user_id}/Status_username")],
            [(await self._lock_label("Zelzal:Lock:hashtak", msg.chat_id), f"{msg.user_id}/Status_tags"), ("التاك : ", f"{msg.user_id}/Status_tags")],
            [("- التالي .. ", f"{msg.user_id}/NextSeting")],
            [("إخفـاء الامـر", f"{msg.user_id}/delAmr")],
        ]
        await self.bot.send_message(msg.chat_id, "\n⇜ اعدادات القروب \n⇜ نعم تعني - مقفل\n⇜ لا تعني - مفتوح\n✓", msg.message_id, reply_markup=inline_keyboard(rows))

    async def _protection_status(self, msg: IncomingMessage) -> None:
        names = {
            "جلب الرابط": "Zelzal:Status:Link",
            "جلب الترحيب": "Zelzal:Status:Welcome",
            "الايدي": "Zelzal:Status:Id",
            "الايدي بالصوره": "Zelzal:Status:IdPhoto",
            "الردود": "Zelzal:Status:Reply",
            "الردود العامه": "Zelzal:Status:ReplySudo",
            "الالعاب": "Zelzal:Status:Games",
        }
        lines = ["\n⇜ اعدادات حماية القروب", "ٴ*⋆┄─┄─┄─┄┄─┄─┄─┄─┄┄⋆*"]
        for label, key in names.items():
            lines.append(f"⇜ {label} ← {'نعم' if await self.store.get(self.store.key(key, msg.chat_id)) else 'لا'}")
        await self.bot.send_message(msg.chat_id, "\n".join(lines), msg.message_id)

    async def _bot_replies_panel(self, msg: IncomingMessage) -> None:
        rows = [
            [("تغييـر الـردود عراقيـة 🇮🇶", f"{msg.user_id}/zelzal_iraq")],
            [("تغييـر الـردود يمنيـة 🇾🇪", f"{msg.user_id}/zelzal_yemen")],
            [("تغييـر الـردود مصريـة 🇪🇬", f"{msg.user_id}/zelzal_egibt")],
            [("تغييـر الـردود سوريـة 🇸🇾", f"{msg.user_id}/zelzal_syria")],
            [("تغييـر الـردود خليجيـة 🇸🇦", f"{msg.user_id}/zelzal_ksa")],
            [("تعطيل ردود البـوت", f"{msg.user_id}/zilzal_zizo")],
            [("✦ اخفاء الامر ✦", f"{msg.user_id}/delAmr")],
        ]
        await self.bot.send_message(msg.chat_id, "*⇜ لـوحـة تحكـم اوامـر ردود البـوت ع حسب اللهجــه ✓*", msg.message_id, reply_markup=inline_keyboard(rows))

    async def _lock_label(self, key: str, chat_id: int) -> str:
        return "نعم" if await self.store.get(self.store.key(key, chat_id)) else "لا"

    def _split_callback(self, data: str) -> tuple[int | None, str]:
        if data.startswith("/"):
            return None, data.lstrip("/")
        if "/" not in data:
            return None, data
        user, action = data.split("/", 1)
        if user.isdigit():
            return int(user), action
        return None, action
