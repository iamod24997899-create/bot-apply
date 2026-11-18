
import os
import json
import sqlite3
import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands


# =========================================================
# CONFIGURATION
# =========================================================

BOT_NAME = "Apply AbelCommunity"
TOKEN = os.getenv("APPLY_TOKEN")
DB_PATH = os.getenv("DB_PATH", "apply_abel.db")
QUESTION_TIMEOUT = 300

# Staff roles
STAFF_TEAM_ROLE_ID = 1525306914106376363
TRIAL_MODERATOR_ROLE_ID = 1525306897219981312

# Leaker roles
LEAKER_TEAM_ROLE_ID = 1568223721406341222
TRIAL_LEAKER_ROLE_ID = 1568223887186198528

# Partnership roles
PARTNERSHIP_MANAGER_ROLE_ID = 1572168269681664080
TRIAL_HEAD_OF_PARTNERSHIP_ROLE_ID = 1571977610630533261
TRIAL_HEAD_COMMUNITY_ROLE_ID = 1571975039983550564
HEADS_ROLE_ID = 1572387480894971904
PROMOTE_DEMOTE_ROLE_ID = 1571928042853499131


# =========================================================
# APPLICATION QUESTIONS
# =========================================================

STAFF_APPLICATION_QUESTIONS = [
    "What is your Discord username, User ID and age?",
    "What is your timezone, and approximately how many hours per day/week can you be active in the server?",
    "Have you had any previous staff experience? If yes, explain your position, responsibilities and how long you held it.",
    "Why do you want to become staff in this server, and what could you contribute to the staff team?",
    "What are your strongest and weakest qualities when working with other people? How could your weaknesses affect you as a staff member?",
    "A member breaks a rule, but they are a close friend of yours. What would you do?",
    "You disagree with another staff member's decision. What would you do?",
    "Which staff roles are you interested in? Select all that apply, or skip this question.",
    "A member repeatedly breaks the rules. After you warn them, they become hostile, insult you and accuse you of abusing your powers. Other members join the argument. Explain how you would handle the situation from beginning to end.",
    "You discover that a staff member who is a close friend has been abusing permissions, punishing members unfairly and giving friends special treatment. You have evidence, but they ask you not to report them. What would you do, and why?",
]

LEAKER_APPLICATION_QUESTIONS = [
    "What is your Discord username, User ID and age?",
    "Do you have any previous experience as a leaker or content provider? If yes, explain what you have done.",
    "What type of content, files, resources or information would you be able to share with Abel Community?",
    "How frequently can you provide new content? Approximately how many valid leaks or files could you share per week?",
    "How do you verify that the files or information you share are genuine, accurate and safe?",
    "Where do you usually find your content, and how do you ensure that you have permission to share it?",
    "What would you do if you discovered that a file you shared was fake, outdated, malicious or contained private information?",
    "Why should Abel Community accept you as a Leaker, and what value could you bring to the community?",
]

PARTNERSHIP_APPLICATION_QUESTIONS = [
    "What is your Discord username, User ID and age?",
    "What is your timezone, and how many hours per day or week can you dedicate to managing partnerships?",
    "Do you have previous experience managing partnerships or working with other Discord communities? Explain your experience.",
    "Why do you want to become a Partnership Manager at Abel Community?",
    "How would you find and approach new communities that could become potential partners?",
    "What criteria would you use to decide whether another server is suitable for a partnership with Abel Community?",
    "A partner server starts breaking our partnership rules or becomes inactive. How would you handle the situation?",
    "Another community asks for a partnership that does not meet our requirements. What would you do?",
    "How would you maintain professional communication with other server owners and partnership teams?",
    "What ideas would you bring to improve Abel Community's partnership program, and why should we select you?"
]

TRIAL_HEAD_COMMUNITY_APPLICATION_QUESTIONS = [
    "What is your Discord username, User ID and age?",
    "What is your timezone, and how much time can you consistently dedicate to leading the Community team?",
    "What previous experience do you have leading teams, managing communities or coordinating staff members? Describe your responsibilities and achievements.",
    "Why do you want to become Trial Head of Community at Abel Community, and what makes you suitable for this leadership position?",
    "How would you organize the Community team, distribute responsibilities and ensure that every team member understands their duties?",
    "Two staff members have a serious disagreement that is affecting the team's work. How would you investigate the situation and resolve it professionally?",
    "A staff member is consistently inactive or failing to complete their responsibilities. How would you address the issue while remaining fair and professional?",
    "How would you handle a decision from another Head that you strongly disagree with? Explain how you would communicate your concerns.",
    "What specific changes or initiatives would you introduce to improve member engagement, community activity and the overall experience in Abel Community?",
    "If you were accepted, what would your priorities be during your first 30 days, and how would you measure whether you had been successful?",
]

FRIEND_RULE_OPTIONS = [
    "Ignore it because they're my friend.",
    "Give them a warning privately and let it slide.",
    "Handle the situation exactly as I would with any other member.",
    "Ask another staff member to deal with it because I know them personally.",
]

STAFF_DISAGREEMENT_OPTIONS = [
    "Argue with them publicly so everyone knows my opinion.",
    "Overrule their decision because I think I'm right.",
    "Ignore it completely.",
    "Discuss it privately with them and, if necessary, bring it to a higher-ranking staff member.",
    "Tell regular members that I disagree with the decision.",
]

STAFF_ROLE_OPTIONS = [
    "Staff Team",
    "Content Creator",
    "Secretary",
    "Application Reader",
    "Appeal Reader",
    "Support Staff",
    "Helper",
]

logging.basicConfig(level=logging.INFO)


def get_questions(app_type):
    if app_type == "leaker":
        return LEAKER_APPLICATION_QUESTIONS
    if app_type == "partnership":
        return PARTNERSHIP_APPLICATION_QUESTIONS
    if app_type == "trial_head_community":
        return TRIAL_HEAD_COMMUNITY_APPLICATION_QUESTIONS
    return STAFF_APPLICATION_QUESTIONS


def get_application_type(application):
    return application.get("app_type") or "staff"


# =========================================================
# DATABASE
# =========================================================

def db_connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with db_connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                guild_id INTEGER PRIMARY KEY,
                review_channel_id INTEGER,
                staff_role_id INTEGER,
                accepted_role_id INTEGER,
                second_accepted_role_id INTEGER,
                leaker_role_id INTEGER
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                answers TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                review_channel_id INTEGER,
                review_message_id INTEGER,
                reason TEXT,
                reviewer_id INTEGER,
                app_type TEXT NOT NULL DEFAULT 'staff',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        settings_columns = {
            row["name"]
            for row in db.execute(
                "PRAGMA table_info(settings)"
            ).fetchall()
        }

        settings_migrations = {
            "second_accepted_role_id": "INTEGER",
            "leaker_role_id": "INTEGER",
        }

        for column, sql_type in settings_migrations.items():
            if column not in settings_columns:
                db.execute(
                    f"ALTER TABLE settings ADD COLUMN {column} {sql_type}"
                )

        app_columns = {
            row["name"]
            for row in db.execute(
                "PRAGMA table_info(applications)"
            ).fetchall()
        }

        app_migrations = {
            "review_channel_id": "INTEGER",
            "review_message_id": "INTEGER",
            "reason": "TEXT",
            "reviewer_id": "INTEGER",
            "app_type": "TEXT NOT NULL DEFAULT 'staff'",
        }

        for column, sql_type in app_migrations.items():
            if column not in app_columns:
                db.execute(
                    f"ALTER TABLE applications ADD COLUMN {column} {sql_type}"
                )


def get_settings(guild_id):
    with db_connect() as db:
        row = db.execute(
            "SELECT * FROM settings WHERE guild_id = ?",
            (guild_id,),
        ).fetchone()

    return dict(row) if row else None


def save_settings(
    guild_id,
    review_channel_id,
    staff_role_id,
    accepted_role_id,
    second_accepted_role_id,
):
    with db_connect() as db:
        db.execute("""
            INSERT INTO settings (
                guild_id,
                review_channel_id,
                staff_role_id,
                accepted_role_id,
                second_accepted_role_id
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                review_channel_id = excluded.review_channel_id,
                staff_role_id = excluded.staff_role_id,
                accepted_role_id = excluded.accepted_role_id,
                second_accepted_role_id = excluded.second_accepted_role_id
        """, (
            guild_id,
            review_channel_id,
            staff_role_id,
            accepted_role_id,
            second_accepted_role_id,
        ))


def create_application(guild_id, user_id, answers, app_type):
    with db_connect() as db:
        columns = db.execute(
            "PRAGMA table_info(applications)"
        ).fetchall()

        column_names_available = {
            row["name"] for row in columns
        }

        data = {
            "guild_id": guild_id,
            "user_id": user_id,
            "answers": json.dumps(answers, ensure_ascii=False),
            "status": "pending",
            "app_type": app_type,
        }

        for column in columns:
            name = column["name"]

            if (
                column["notnull"]
                and column["dflt_value"] is None
                and name not in data
                and name not in ("id",)
                and column["pk"] == 0
            ):
                if name == "created_at":
                    continue
                elif name == "reason":
                    data[name] = ""
                elif name in (
                    "review_channel_id",
                    "review_message_id",
                    "reviewer_id",
                    "staff_role_id",
                    "accepted_role_id",
                    "second_accepted_role_id",
                    "leaker_role_id",
                ):
                    data[name] = 0
                elif name in (
                    "app_type",
                    "application_type",
                    "type",
                ):
                    data[name] = app_type
                elif name == "status":
                    data[name] = "pending"

        insert_columns = [
            name for name in data
            if name in column_names_available
        ]

        placeholders = ", ".join("?" for _ in insert_columns)
        names_sql = ", ".join(insert_columns)
        values = [data[name] for name in insert_columns]

        cursor = db.execute(
            f"INSERT INTO applications ({names_sql}) "
            f"VALUES ({placeholders})",
            values,
        )

        return cursor.lastrowid


def get_application(application_id):
    with db_connect() as db:
        row = db.execute(
            "SELECT * FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()

    return dict(row) if row else None


def get_application_by_review_message(message_id):
    with db_connect() as db:
        row = db.execute("""
            SELECT * FROM applications
            WHERE review_message_id = ?
        """, (message_id,)).fetchone()

    return dict(row) if row else None


def set_review_message(application_id, channel_id, message_id):
    with db_connect() as db:
        db.execute("""
            UPDATE applications
            SET review_channel_id = ?, review_message_id = ?
            WHERE id = ?
        """, (channel_id, message_id, application_id))


def finish_application(application_id, status, reason, reviewer_id):
    with db_connect() as db:
        db.execute("""
            UPDATE applications
            SET status = ?, reason = ?, reviewer_id = ?
            WHERE id = ? AND status = 'pending'
        """, (status, reason, reviewer_id, application_id))

        return db.execute("SELECT changes()").fetchone()[0] == 1


# =========================================================
# APPLICATION SESSION / CANCELLATION
# =========================================================

class ApplicationSession:
    def __init__(self):
        self.cancelled = asyncio.Event()


class CancelApplicationView(discord.ui.View):
    def __init__(self, session):
        super().__init__(timeout=QUESTION_TIMEOUT)
        self.session = session

    @discord.ui.button(
        label="Cancel Application",
        style=discord.ButtonStyle.danger,
        emoji="\u274C",
        custom_id="apply_abel:cancel_application",
    )
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.session.cancelled.set()
        self.stop()

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(view=self)

        try:
            await interaction.user.send(
                "Your application has been cancelled."
            )
        except discord.HTTPException:
            pass


# =========================================================
# QUESTION SELECTION VIEWS
# =========================================================

class ChoiceButton(discord.ui.Button):
    def __init__(self, label, index, parent_view):
        super().__init__(
            label=f"Option {index + 1}",
            style=discord.ButtonStyle.secondary,
            custom_id=f"apply_abel:choice:{index}",
            row=index // 2,
        )
        self.choice_label = label
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if self.parent_view.answer is not None:
            await interaction.response.send_message(
                "You have already selected an answer.",
                ephemeral=True,
            )
            return

        if self.parent_view.session.cancelled.is_set():
            await interaction.response.send_message(
                "This application has been cancelled.",
                ephemeral=True,
            )
            return

        self.parent_view.answer = self.choice_label
        self.parent_view.stop()

        for child in self.parent_view.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=f"Selected: **{self.choice_label}**",
            view=self.parent_view,
        )


class MultipleChoiceView(discord.ui.View):
    def __init__(self, options, session):
        super().__init__(timeout=QUESTION_TIMEOUT)
        self.answer = None
        self.session = session

        for index, option in enumerate(options):
            self.add_item(ChoiceButton(option, index, self))

        self.add_item(CancelChoiceButton(session, self))


class CancelChoiceButton(discord.ui.Button):
    def __init__(self, session, parent_view):
        super().__init__(
            label="Cancel Application",
            style=discord.ButtonStyle.danger,
            emoji="\u274C",
            row=4,
            custom_id="apply_abel:cancel_choice",
        )
        self.session = session
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.session.cancelled.set()
        self.parent_view.stop()

        for child in self.parent_view.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="Your application has been cancelled.",
            view=self.parent_view,
        )

        try:
            await interaction.user.send(
                "Your application has been cancelled."
            )
        except discord.HTTPException:
            pass


class RoleSelectView(discord.ui.View):
    def __init__(self, session):
        super().__init__(timeout=QUESTION_TIMEOUT)
        self.session = session
        self.selected_roles = []
        self.finished = False

        self.role_select = discord.ui.Select(
            placeholder="Choose the staff roles you're interested in",
            min_values=1,
            max_values=len(STAFF_ROLE_OPTIONS),
            options=[
                discord.SelectOption(label=role, value=role)
                for role in STAFF_ROLE_OPTIONS
            ],
        )
        self.role_select.callback = self.select_roles
        self.add_item(self.role_select)

    async def select_roles(self, interaction: discord.Interaction):
        self.selected_roles = list(self.role_select.values)

        await interaction.response.send_message(
            "Selection saved. Press **Submit Roles** to continue.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Submit Roles",
        style=discord.ButtonStyle.success,
        emoji="\u2705",
        row=1,
    )
    async def submit_roles(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not self.selected_roles:
            await interaction.response.send_message(
                "Please select at least one role, or choose Skip.",
                ephemeral=True,
            )
            return

        self.finished = True
        self.stop()

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="Selected roles: " + ", ".join(self.selected_roles),
            view=self,
        )

    @discord.ui.button(
        label="Skip Question",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def skip_roles(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.selected_roles = []
        self.finished = True
        self.stop()

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="You skipped this question.",
            view=self,
        )

    @discord.ui.button(
        label="Cancel Application",
        style=discord.ButtonStyle.danger,
        emoji="\u274C",
        row=2,
    )
    async def cancel_roles(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.session.cancelled.set()
        self.stop()

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="Your application has been cancelled.",
            view=self,
        )

        try:
            await interaction.user.send(
                "Your application has been cancelled."
            )
        except discord.HTTPException:
            pass


# =========================================================
# BOT SETUP
# =========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True


class ApplyBot(commands.Bot):
    async def setup_hook(self):
        init_db()

        self.add_view(ApplicationPanelView())
        self.add_view(ApplicationReviewView())

        try:
            synced = await self.tree.sync()
            logging.info("Synced %s slash commands.", len(synced))
        except Exception:
            logging.exception("Could not sync slash commands.")


bot = ApplyBot(
    command_prefix="!",
    intents=intents,
)


@bot.event
async def on_ready():
    print("=" * 45)
    print(f"Bot: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Servers: {len(bot.guilds)}")
    print(f"{BOT_NAME} is ready.")
    print("=" * 45)


# =========================================================
# PERMISSIONS AND EMBEDS
# =========================================================

async def check_review_permission(interaction):
    if not interaction.guild or not isinstance(
        interaction.user, discord.Member
    ):
        await interaction.response.send_message(
            "This action can only be used inside the server.",
            ephemeral=True,
        )
        return False

    settings = get_settings(interaction.guild.id)

    if not settings:
        await interaction.response.send_message(
            "The application system has not been configured.",
            ephemeral=True,
        )
        return False

    staff_role_id = settings.get("staff_role_id")
    has_staff_role = (
        staff_role_id is not None
        and any(
            role.id == staff_role_id
            for role in interaction.user.roles
        )
    )

    if (
        not has_staff_role
        and not interaction.user.guild_permissions.manage_guild
    ):
        await interaction.response.send_message(
            "You do not have permission to review applications.",
            ephemeral=True,
        )
        return False

    return True


def build_application_embed(application):
    answers = json.loads(application["answers"])
    app_type = get_application_type(application)
    questions = get_questions(app_type)

    status = application["status"].lower()

    if status == "accepted":
        embed_color = discord.Color.green()
    elif status == "rejected":
        embed_color = discord.Color.red()
    else:
        embed_color = discord.Color.blurple()

    application_name = {
        "leaker": "Leaker Application",
        "partnership": "Partnership Manager Application",
        "trial_head_community": "Trial Head of Community Application",
    }.get(app_type, "Staff Application")

    embed = discord.Embed(
        title=application_name,
        color=embed_color,
    )

    embed.add_field(
        name="Applicant",
        value=f"<@{application['user_id']}>",
        inline=False,
    )
    embed.add_field(
        name="User ID",
        value=str(application["user_id"]),
        inline=True,
    )
    embed.add_field(
        name="Status",
        value=status.capitalize(),
        inline=True,
    )

    for index, answer in enumerate(answers):
        if index >= len(questions):
            break

        question = questions[index]
        answer_text = (
            str(answer).strip()
            if answer
            else "No answer provided."
        )

        if len(answer_text) > 1000:
            answer_text = answer_text[:997] + "..."

        embed.add_field(
            name=f"Q{index + 1}. {question[:240]}",
            value=answer_text,
            inline=False,
        )

    if application.get("reason"):
        embed.add_field(
            name="Review reason",
            value=application["reason"][:1024],
            inline=False,
        )

    if application.get("reviewer_id"):
        embed.add_field(
            name="Reviewed by",
            value=f"<@{application['reviewer_id']}>",
            inline=False,
        )

    embed.set_footer(text=BOT_NAME)
    return embed


# =========================================================
# ASK APPLICATION QUESTIONS
# =========================================================

async def wait_for_dm_answer(
    user,
    session,
    question,
    number,
    total_questions,
):
    await user.send(
        f"**Question {number}/{total_questions}**\n"
        f"{question}",
        view=CancelApplicationView(session),
    )

    def check(message):
        return (
            message.author.id == user.id
            and isinstance(message.channel, discord.DMChannel)
        )

    message_task = asyncio.create_task(
        bot.wait_for(
            "message",
            check=check,
            timeout=QUESTION_TIMEOUT,
        )
    )
    cancel_task = asyncio.create_task(session.cancelled.wait())

    done, pending = await asyncio.wait(
        [message_task, cancel_task],
        timeout=QUESTION_TIMEOUT,
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    if session.cancelled.is_set():
        return None

    if not done:
        raise asyncio.TimeoutError

    if message_task in done:
        try:
            message = message_task.result()
        except asyncio.TimeoutError:
            raise

        if message.content.strip().lower() == "cancel":
            session.cancelled.set()
            return None

        answer = message.content.strip()

        if message.attachments:
            attachment_urls = "\n".join(
                attachment.url for attachment in message.attachments
            )
            answer = (answer + "\n" + attachment_urls).strip()

        if not answer:
            await user.send(
                "Please provide an answer before continuing."
            )
            return await wait_for_dm_answer(
                user,
                session,
                question,
                number,
                total_questions,
            )

        return answer

    return None


async def ask_multiple_choice(
    user,
    session,
    question,
    number,
    options,
    total_questions,
):
    view = MultipleChoiceView(options, session)

    choices_text = "\n".join(
        f"**Option {index + 1}:** {option}"
        for index, option in enumerate(options)
    )

    await user.send(
        f"**Question {number}/{total_questions}**\n"
        f"{question}\n\n"
        f"{choices_text}\n\n"
        "Click the button matching your answer below.",
        view=view,
    )

    timed_out = await view.wait()

    if session.cancelled.is_set():
        return None

    if timed_out:
        raise asyncio.TimeoutError

    if view.answer is None:
        raise asyncio.TimeoutError

    logging.info(
        "User %s selected an answer for question %s.",
        user.id,
        number,
    )

    return view.answer


async def ask_roles(
    user,
    session,
    question,
    number,
    total_questions,
):
    view = RoleSelectView(session)

    await user.send(
        f"**Question {number}/{total_questions}**\n"
        f"{question}\n\n"
        "Select one or more roles, then press **Submit Roles**. "
        "You can also skip this question.",
        view=view,
    )

    timed_out = await view.wait()

    if session.cancelled.is_set():
        return None

    if timed_out or not view.finished:
        raise asyncio.TimeoutError

    return ", ".join(view.selected_roles) if view.selected_roles else "Skipped"


async def ask_application_questions(user, app_type):
    session = ApplicationSession()
    answers = []
    questions = get_questions(app_type)
    total_questions = len(questions)

    application_name = {
        "leaker": "Leaker",
        "partnership": "Partnership Manager",
        "trial_head_community": "Trial Head of Community",
    }.get(app_type, "Staff")

    try:
        await user.send(
            f"Welcome to the **Apply AbelCommunity {application_name} Application**!\n"
            f"You will answer {total_questions} questions one by one.\n"
            "You have 5 minutes to answer each question.\n"
            "Use the **Cancel Application** button at any time, or type "
            "`cancel` when answering a text question."
        )
    except discord.Forbidden:
        return None

    try:
        for number, question in enumerate(questions, start=1):
            if session.cancelled.is_set():
                return None

            if app_type == "staff" and number == 6:
                answer = await ask_multiple_choice(
                    user,
                    session,
                    question,
                    number,
                    FRIEND_RULE_OPTIONS,
                    total_questions,
                )

            elif app_type == "staff" and number == 7:
                answer = await ask_multiple_choice(
                    user,
                    session,
                    question,
                    number,
                    STAFF_DISAGREEMENT_OPTIONS,
                    total_questions,
                )

            elif app_type == "staff" and number == 8:
                answer = await ask_roles(
                    user,
                    session,
                    question,
                    number,
                    total_questions,
                )

            else:
                answer = await wait_for_dm_answer(
                    user,
                    session,
                    question,
                    number,
                    total_questions,
                )

            if answer is None:
                if not session.cancelled.is_set():
                    await user.send(
                        "Your application was not completed because "
                        "the question timed out or could not be answered. "
                        "Please start again later."
                    )
                return None

            answers.append(answer)

        return answers

    except asyncio.TimeoutError:
        try:
            await user.send(
                "Your application timed out because you did not answer "
                "within 5 minutes. Please start again later."
            )
        except discord.HTTPException:
            pass

        return None

    except discord.Forbidden:
        logging.warning(
            "The bot could not DM user %s during the application.",
            user.id,
        )
        return None

    except discord.HTTPException:
        logging.exception(
            "A Discord API error occurred during the application for user %s.",
            user.id,
        )
        try:
            await user.send(
                "Discord encountered an error while processing your "
                "application. Please start again later."
            )
        except discord.HTTPException:
            pass
        return None


# =========================================================
# START APPLICATION
# =========================================================

async def start_application(interaction, app_type):
    if interaction.guild is None:
        await interaction.response.send_message(
            "Start your application from the server.",
            ephemeral=True,
        )
        return

    if app_type in ("partnership", "trial_head_community") and not any(
        role.id == STAFF_TEAM_ROLE_ID for role in interaction.user.roles
    ):
        await interaction.response.send_message(
            "Only members of the Staff Team can apply for this position.",
            ephemeral=True,
        )
        return

    settings = get_settings(interaction.guild.id)

    if not settings or not settings.get("review_channel_id"):
        await interaction.response.send_message(
            "The application system has not been configured yet.",
            ephemeral=True,
        )
        return

    required_role_ids = {
        "leaker": [
            LEAKER_TEAM_ROLE_ID,
            TRIAL_LEAKER_ROLE_ID,
        ],
        "partnership": [
            PARTNERSHIP_MANAGER_ROLE_ID,
            TRIAL_HEAD_OF_PARTNERSHIP_ROLE_ID,
            HEADS_ROLE_ID,
        ],
        "trial_head_community": [
            TRIAL_HEAD_COMMUNITY_ROLE_ID,
            HEADS_ROLE_ID,
            PROMOTE_DEMOTE_ROLE_ID,
        ],
    }.get(app_type, [
        STAFF_TEAM_ROLE_ID,
        TRIAL_MODERATOR_ROLE_ID,
    ])

    missing_roles = [
        role_id for role_id in required_role_ids
        if interaction.guild.get_role(role_id) is None
    ]

    if missing_roles:
        await interaction.response.send_message(
            "One or more application roles could not be found. "
            "Please contact the staff team.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        "I've sent you a DM to start your application.",
        ephemeral=True,
    )

    answers = await ask_application_questions(
        interaction.user,
        app_type,
    )

    if answers is None:
        return

    try:
        application_id = create_application(
            interaction.guild.id,
            interaction.user.id,
            answers,
            app_type,
        )
    except sqlite3.Error:
        logging.exception("Could not save the application.")
        try:
            await interaction.user.send(
                "I couldn't save your application because of a database "
                "error. Please contact the server staff."
            )
        except discord.HTTPException:
            pass
        return

    application = get_application(application_id)
    embed = build_application_embed(application)

    review_channel = interaction.guild.get_channel(
        settings["review_channel_id"]
    )

    if review_channel is None:
        try:
            review_channel = await interaction.guild.fetch_channel(
                settings["review_channel_id"]
            )
        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
        ):
            review_channel = None

    if review_channel is None:
        try:
            await interaction.user.send(
                "Your answers were collected, but the review channel "
                "could not be found. Please contact the server staff."
            )
        except discord.HTTPException:
            pass
        return

    try:
        review_message = await review_channel.send(
            embed=embed,
            view=ApplicationReviewView(),
            allowed_mentions=discord.AllowedMentions.none(),
        )

        set_review_message(
            application_id,
            review_channel.id,
            review_message.id,
        )

        await interaction.user.send(
            f"Your {app_type} application has been submitted successfully. "
            "The staff team will review it."
        )

    except discord.Forbidden:
        try:
            await interaction.user.send(
                "The bot cannot post in the review channel. "
                "Please contact the server staff."
            )
        except discord.HTTPException:
            pass


# =========================================================
# APPLICATION PANEL
# =========================================================

class ApplicationPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Staff Apply",
        style=discord.ButtonStyle.primary,
        emoji="\U0001F4DD",
        custom_id="apply_abel:start_staff",
        row=0,
    )
    async def apply_staff_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await start_application(interaction, "staff")

    @discord.ui.button(
        label="Leaker Apply",
        style=discord.ButtonStyle.primary,
        emoji="\U0001F4DD",
        custom_id="apply_abel:start_leaker",
        row=0,
    )
    async def apply_leaker_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await start_application(interaction, "leaker")

    @discord.ui.button(
        label="Partnership Manager Apply",
        style=discord.ButtonStyle.primary,
        emoji="💎",
        custom_id="apply_abel:start_partnership",
        row=1,
    )
    async def apply_partnership_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await start_application(interaction, "partnership")

    @discord.ui.button(
        label="Trial Head Community Apply",
        style=discord.ButtonStyle.primary,
        emoji="\U0001F451",
        custom_id="apply_abel:start_trial_head_community",
        row=1,
    )
    async def apply_trial_head_community_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await start_application(interaction, "trial_head_community")


# =========================================================
# REVIEW REASON MODAL
# =========================================================

class ReviewReasonModal(discord.ui.Modal):
    def __init__(self, accepted, application_id):
        self.accepted = accepted
        self.application_id = application_id

        title = "Accept Application" if accepted else "Reject Application"
        super().__init__(title=title, timeout=300)

        self.reason = discord.ui.TextInput(
            label="Reason",
            placeholder="Write the reason here...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        allowed = await check_review_permission(interaction)
        if not allowed:
            return

        application = get_application(self.application_id)

        if not application:
            await interaction.response.send_message(
                "Could not find this application.",
                ephemeral=True,
            )
            return

        await process_review_decision(
            interaction=interaction,
            application=application,
            accepted=self.accepted,
            reason=str(self.reason.value).strip(),
        )


# =========================================================
# APPLICATION REVIEW BUTTONS
# =========================================================

class ApplicationReviewView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def decide_without_reason(self, interaction, accepted):
        allowed = await check_review_permission(interaction)
        if not allowed:
            return

        if interaction.message is None:
            await interaction.response.send_message(
                "Could not find the application message.",
                ephemeral=True,
            )
            return

        application = get_application_by_review_message(
            interaction.message.id
        )

        if not application:
            await interaction.response.send_message(
                "Could not find this application.",
                ephemeral=True,
            )
            return

        await process_review_decision(
            interaction=interaction,
            application=application,
            accepted=accepted,
            reason="No reason provided.",
        )

    @discord.ui.button(
        label="Accept",
        style=discord.ButtonStyle.success,
        emoji="\u2705",
        custom_id="apply_abel:accept_direct",
        row=0,
    )
    async def accept_direct(self, interaction, button):
        await self.decide_without_reason(interaction, True)

    @discord.ui.button(
        label="Accept with Reason",
        style=discord.ButtonStyle.success,
        emoji="\U0001F4DD",
        custom_id="apply_abel:accept",
        row=0,
    )
    async def accept_with_reason(self, interaction, button):
        allowed = await check_review_permission(interaction)
        if not allowed:
            return

        application = get_application_by_review_message(
            interaction.message.id if interaction.message else 0
        )

        if not application or application["status"] != "pending":
            await interaction.response.send_message(
                "This application has already been reviewed or could not "
                "be found.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            ReviewReasonModal(
                accepted=True,
                application_id=application["id"],
            )
        )

    @discord.ui.button(
        label="Reject",
        style=discord.ButtonStyle.danger,
        emoji="\u274C",
        custom_id="apply_abel:reject_direct",
        row=1,
    )
    async def reject_direct(self, interaction, button):
        await self.decide_without_reason(interaction, False)

    @discord.ui.button(
        label="Reject with Reason",
        style=discord.ButtonStyle.danger,
        emoji="\U0001F4DD",
        custom_id="apply_abel:reject",
        row=1,
    )
    async def reject_with_reason(self, interaction, button):
        allowed = await check_review_permission(interaction)
        if not allowed:
            return

        application = get_application_by_review_message(
            interaction.message.id if interaction.message else 0
        )

        if not application or application["status"] != "pending":
            await interaction.response.send_message(
                "This application has already been reviewed or could not "
                "be found.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            ReviewReasonModal(
                accepted=False,
                application_id=application["id"],
            )
        )


# =========================================================
# PROCESS ACCEPT / REJECT
# =========================================================

async def process_review_decision(
    interaction,
    application,
    accepted,
    reason,
):
    if application["status"] != "pending":
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "This application has already been reviewed.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "This application has already been reviewed.",
                ephemeral=True,
            )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    new_status = "accepted" if accepted else "rejected"

    saved = finish_application(
        application_id=application["id"],
        status=new_status,
        reason=reason,
        reviewer_id=interaction.user.id,
    )

    if not saved:
        await interaction.followup.send(
            "This application has already been reviewed.",
            ephemeral=True,
        )
        return

    guild = interaction.guild
    settings = get_settings(application["guild_id"])
    result_messages = []
    member = None
    app_type = get_application_type(application)

    application_name = {
        "leaker": "Leaker",
        "partnership": "Partnership Manager",
        "trial_head_community": "Trial Head of Community",
    }.get(app_type, "Staff")

    if guild:
        try:
            member = guild.get_member(application["user_id"])
            if member is None:
                member = await guild.fetch_member(
                    application["user_id"]
                )
        except (discord.NotFound, discord.HTTPException):
            member = None

    if accepted and member and settings:
        role_ids = {
            "leaker": [
                LEAKER_TEAM_ROLE_ID,
                TRIAL_LEAKER_ROLE_ID,
            ],
            "partnership": [
                TRIAL_HEAD_OF_PARTNERSHIP_ROLE_ID,
                PARTNERSHIP_MANAGER_ROLE_ID,
                HEADS_ROLE_ID,
            ],
            "trial_head_community": [
                TRIAL_HEAD_COMMUNITY_ROLE_ID,
                HEADS_ROLE_ID,
                PROMOTE_DEMOTE_ROLE_ID,
            ],
        }.get(app_type, [
            STAFF_TEAM_ROLE_ID,
            TRIAL_MODERATOR_ROLE_ID,
        ])

        roles_to_add = []

        for role_id in role_ids:
            role = guild.get_role(role_id) if guild else None

            if role is None:
                result_messages.append(
                    f"Role ID {role_id} could not be found."
                )
                continue

            roles_to_add.append(role)

        if roles_to_add:
            try:
                await member.add_roles(
                    *roles_to_add,
                    reason=(
                        f"{app_type.capitalize()} application "
                        f"#{application['id']} accepted"
                    ),
                )
            except discord.Forbidden:
                result_messages.append(
                    "I don't have permission to assign one or more roles. "
                    "Check my Manage Roles permission and role hierarchy."
                )
            except discord.HTTPException:
                result_messages.append(
                    "Could not assign one or more application roles."
                )

    elif accepted and member is None:
        result_messages.append(
            "The applicant is no longer in the server; no roles were assigned."
        )

    updated_application = get_application(application["id"])
    updated_embed = build_application_embed(updated_application)

    review_message = interaction.message

    if review_message is None and guild:
        channel_id = application.get("review_channel_id")
        message_id = application.get("review_message_id")

        if channel_id and message_id:
            channel = guild.get_channel(channel_id)

            if channel is None:
                try:
                    channel = await guild.fetch_channel(channel_id)
                except (
                    discord.NotFound,
                    discord.Forbidden,
                    discord.HTTPException,
                ):
                    channel = None

            if channel:
                try:
                    review_message = await channel.fetch_message(
                        message_id
                    )
                except (
                    discord.NotFound,
                    discord.Forbidden,
                    discord.HTTPException,
                ):
                    review_message = None

    if review_message:
        disabled_view = ApplicationReviewView()

        for child in disabled_view.children:
            child.disabled = True

        try:
            await review_message.edit(
                embed=updated_embed,
                view=disabled_view,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            result_messages.append(
                "The review message could not be updated."
            )

    if member:
        try:
            server_name = guild.name if guild else "the server"

            if accepted:
                dm_text = (
                    f"ðŸŽ‰ Your **{application_name} application** for "
                    f"**{server_name}** has been accepted!\n"
                    f"**Reason:** {reason}"
                )
            else:
                dm_text = (
                    f"Unfortunately, your **{application_name} application** "
                    f"for **{server_name}** has been rejected.\n"
                    f"**Reason:** {reason}"
                )

            await member.send(dm_text)

        except discord.Forbidden:
            result_messages.append(
                "The applicant's DMs are closed, so I could not notify them."
            )
        except discord.HTTPException:
            result_messages.append(
                "I could not send the applicant a DM."
            )

    message = (
        f"{application_name} application "
        f"has been **{new_status}**."
    )

    if result_messages:
        message += "\n\n" + "\n".join(
            f"âš ï¸ {item}" for item in result_messages
        )

    await interaction.followup.send(message, ephemeral=True)


# =========================================================
# SLASH COMMAND: SETUP
# =========================================================

@bot.tree.command(
    name="applysetup",
    description="Configure the application system.",
)
@app_commands.describe(
    review_channel="Channel where applications will be posted",
    staff_role="Role allowed to review applications",
)
@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
async def applysetup(
    interaction: discord.Interaction,
    review_channel: discord.TextChannel,
    staff_role: discord.Role = None,
):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "You need the Manage Server permission to configure this.",
            ephemeral=True,
        )
        return

    save_settings(
        guild_id=interaction.guild.id,
        review_channel_id=review_channel.id,
        staff_role_id=staff_role.id if staff_role else None,
        accepted_role_id=STAFF_TEAM_ROLE_ID,
        second_accepted_role_id=TRIAL_MODERATOR_ROLE_ID,
    )

    staff_role_text = (
        staff_role.mention
        if staff_role
        else "Manage Server permission"
    )

    await interaction.response.send_message(
        "**Application system configured successfully.**\n\n"
        f"**Review channel:** {review_channel.mention}\n\n"
        "**Staff application roles:**\n"
        f"â€¢ Staff Team: <@&{STAFF_TEAM_ROLE_ID}>\n"
        f"â€¢ Trial Moderator: <@&{TRIAL_MODERATOR_ROLE_ID}>\n\n"
        "**Leaker application roles:**\n"
        f"â€¢ Leaker Team: <@&{LEAKER_TEAM_ROLE_ID}>\n"
        f"â€¢ Trial Leaker: <@&{TRIAL_LEAKER_ROLE_ID}>\n\n"
        "**Partnership application roles:**\n"
        f"â€¢ Partnership Manager: <@&{PARTNERSHIP_MANAGER_ROLE_ID}>\n"
        f"â€¢ Trial Head of Partnership: <@&{TRIAL_HEAD_OF_PARTNERSHIP_ROLE_ID}>\n\n"
        f"**Staff review permission:** {staff_role_text}",
        ephemeral=True,
    )


# =========================================================
# SHARED PANEL EMBED
# =========================================================

def build_panel_embed():
    embed = discord.Embed(
        title="Applications | Abel Community",
        description=(
            "Interested in joining our Staff Team, becoming a Leaker, managing partnerships, or leading the Community team?\n\n"
            "Choose the application you want to submit using the buttons below. "
            "The bot will send you the questions through direct messages.\n\n"
            "Please answer honestly and wait for the staff team to review "
            "your application."
        ),
        color=discord.Color.blurple(),
    )
    embed.set_footer(text=BOT_NAME)
    return embed


def get_missing_application_roles(guild):
    required_role_ids = [
        STAFF_TEAM_ROLE_ID,
        TRIAL_MODERATOR_ROLE_ID,
        LEAKER_TEAM_ROLE_ID,
        TRIAL_LEAKER_ROLE_ID,
        PARTNERSHIP_MANAGER_ROLE_ID,
        TRIAL_HEAD_OF_PARTNERSHIP_ROLE_ID,
        TRIAL_HEAD_COMMUNITY_ROLE_ID,
        HEADS_ROLE_ID,
        PROMOTE_DEMOTE_ROLE_ID,
    ]

    return [
        role_id
        for role_id in required_role_ids
        if guild.get_role(role_id) is None
    ]


# =========================================================
# SLASH COMMAND: PANEL
# =========================================================

@bot.tree.command(
    name="applypanel",
    description="Send the application panel.",
)
@app_commands.describe(
    channel="Channel where the application panel will be sent",
)
@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
async def applypanel(
    interaction: discord.Interaction,
    channel: discord.TextChannel = None,
):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "You need the Manage Server permission to use this command.",
            ephemeral=True,
        )
        return

    settings = get_settings(interaction.guild.id)

    if not settings or not settings.get("review_channel_id"):
        await interaction.response.send_message(
            "Run `/applysetup` before creating the panel.",
            ephemeral=True,
        )
        return

    missing_roles = get_missing_application_roles(interaction.guild)

    if missing_roles:
        await interaction.response.send_message(
            "One or more application roles could not be found. "
            "Please check the role IDs in the bot configuration.",
            ephemeral=True,
        )
        return

    target_channel = channel or interaction.channel

    try:
        await target_channel.send(
            embed=build_panel_embed(),
            view=ApplicationPanelView(),
            allowed_mentions=discord.AllowedMentions.none(),
        )

        await interaction.response.send_message(
            f"Application panel sent to {target_channel.mention}.",
            ephemeral=True,
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I don't have permission to send messages in that channel.",
            ephemeral=True,
        )


# =========================================================
# SLASH COMMAND: REPLACE EXISTING PANEL
# =========================================================

@bot.tree.command(
    name="applypanelreplace",
    description="Replace the existing application panel with the updated one.",
)
@app_commands.describe(
    channel="Channel containing the old application panel",
)
@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
async def applypanelreplace(
    interaction: discord.Interaction,
    channel: discord.TextChannel = None,
):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "You need the Manage Server permission to use this command.",
            ephemeral=True,
        )
        return

    settings = get_settings(interaction.guild.id)

    if not settings or not settings.get("review_channel_id"):
        await interaction.response.send_message(
            "Run `/applysetup` before replacing the panel.",
            ephemeral=True,
        )
        return

    missing_roles = get_missing_application_roles(interaction.guild)

    if missing_roles:
        await interaction.response.send_message(
            "One or more application roles could not be found. "
            "Please check the role IDs.",
            ephemeral=True,
        )
        return

    target_channel = channel or interaction.channel

    await interaction.response.defer(ephemeral=True)

    try:
        async for message in target_channel.history(limit=100):
            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            old_embed = message.embeds[0]

            # Only replace the application panel, not application reviews.
            if old_embed.title not in ("Apply for Staff", "Applications | Abel Community"):
                continue

            await message.edit(
                embed=build_panel_embed(),
                view=ApplicationPanelView(),
                allowed_mentions=discord.AllowedMentions.none(),
            )

            await interaction.followup.send(
                "**Application panel replaced successfully!**\n"
                f"Updated the existing panel in {target_channel.mention}.\n"
                "The Staff Apply, Leaker Apply, Partnership Manager Apply, and Trial Head Community Apply buttons are now available.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            "I couldn't find the old application panel in the last "
            "100 messages of that channel. Use `/applypanel` to send a new one.",
            ephemeral=True,
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "I don't have permission to read or edit messages in that channel.",
            ephemeral=True,
        )
    except discord.HTTPException:
        logging.exception("Could not replace the application panel.")
        await interaction.followup.send(
            "An error occurred while replacing the application panel.",
            ephemeral=True,
        )


# =========================================================
# ERROR HANDLING
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
):
    logging.error(
        "Application command error",
        exc_info=(type(error), error, error.__traceback__),
    )

    message = (
        "An error occurred while executing the command. "
        "Check the bot console for details."
    )

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True,
            )
    except discord.HTTPException:
        pass


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":
    init_db()

    if not TOKEN:
        raise RuntimeError(
            "Missing APPLY_TOKEN environment variable. "
            "Set APPLY_TOKEN to your Discord bot token."
        )

    bot.run(TOKEN)












