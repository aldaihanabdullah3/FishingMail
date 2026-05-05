"""
email_generator.py
==================
Template-based email generation — no LLMs involved.

Strategy:
  1. Categorised email templates (IT, HR, Finance, Vendor, Colleague, Management)
  2. Faker fills in names, dates, numbers, company names, etc.
  3. A weighted random draw picks a category, then a template within it.
  4. Each template declares its own attachment probability + accepted types.

Adding more variety is easy: drop a new dict into the relevant TEMPLATES list.
"""

import random
import textwrap
from datetime import datetime, timedelta
from faker import Faker

fk = Faker("en_US")

# --------------------------------------------------------------------------- #
# Template corpus                                                               #
# --------------------------------------------------------------------------- #
# Each template dict keys:
#   subject  – f-string evaluated with a ctx dict supplied by _make_ctx()
#   body     – same
#   attach_p – probability [0,1] that this email has an attachment
#   attach_types – list of possible attachment type tags (see attachment_generator)

TEMPLATES: dict[str, list[dict]] = {

    # ── IT / Security ────────────────────────────────────────────────────── #
    "it": [
        {
            "subject": "ACTION REQUIRED: Your password expires in {days} day(s)",
            "body": textwrap.dedent("""\
                Dear {first_name},

                Our records indicate that your network password will expire in {days} day(s)
                on {expire_date}.

                Please update your password before the deadline to avoid being locked out
                of company systems.

                To change your password:
                  1. Press Ctrl+Alt+Delete and choose "Change a password"
                  2. Or visit the employee self-service portal

                If you have already updated your password, please disregard this message.

                IT Help Desk
                {company} Information Technology
                helpdesk@{domain} | Ext. {ext}
            """),
            "attach_p": 0.10,
            "attach_types": ["pdf"],
        },
        {
            "subject": "Scheduled Maintenance: {system} — {maint_date}",
            "body": textwrap.dedent("""\
                Dear {first_name},

                Please be advised of scheduled maintenance for {system}:

                  Date/Time : {maint_date} at {maint_time} (local time)
                  Duration  : approximately {duration} hours
                  Impact    : {impact}

                During this window the system will be unavailable. Please plan accordingly
                and save any open work before the maintenance begins.

                If you have questions, please contact the IT Help Desk.

                Regards,
                IT Operations — {company}
            """),
            "attach_p": 0.20,
            "attach_types": ["pdf", "xlsx"],
        },
        {
            "subject": "New MFA Enrollment Required for Your Account",
            "body": textwrap.dedent("""\
                Hi {first_name},

                As part of our ongoing security improvements, all employees are required to
                enroll in Multi-Factor Authentication (MFA) by {deadline}.

                Steps to enroll:
                  1. Download the authenticator app from your device's app store
                  2. Scan the QR code in the attached setup guide
                  3. Enter the 6-digit code to verify

                After enrollment, you will be prompted for an MFA code at each login.

                Please complete this by {deadline} to avoid disruption to your access.

                Security Team
                {company}
            """),
            "attach_p": 0.60,
            "attach_types": ["pdf"],
        },
        {
            "subject": "VPN Client Update — Version {version} Now Available",
            "body": textwrap.dedent("""\
                Dear {first_name},

                A new version of the corporate VPN client (v{version}) is now available.
                This update includes important security patches and performance improvements.

                Please update at your earliest convenience:
                  • Download the installer from IT Software Center
                  • Run the setup wizard and follow the prompts
                  • Restart your machine after installation

                The previous version ({old_version}) will reach end-of-support on {eol_date}.

                For assistance, contact the Help Desk at helpdesk@{domain}.

                IT Infrastructure
            """),
            "attach_p": 0.30,
            "attach_types": ["pdf", "zip"],
        },
        {
            "subject": "Reminder: Mandatory Security Awareness Training Due {deadline}",
            "body": textwrap.dedent("""\
                Hi {first_name},

                Our records show you have not yet completed the mandatory annual security
                awareness training module. This training is required for all {company} staff.

                Deadline: {deadline}

                The course takes approximately 45 minutes and covers:
                  • Phishing recognition
                  • Password hygiene
                  • Data handling and classification
                  • Incident reporting procedures

                Please log in to the Learning Management System and complete the course.

                Non-completion may result in a temporary suspension of system access.

                HR & Compliance
                {company}
            """),
            "attach_p": 0.15,
            "attach_types": ["pdf"],
        },
    ],

    # ── HR ───────────────────────────────────────────────────────────────── #
    "hr": [
        {
            "subject": "Reminder: Submit Your Timesheet by {deadline}",
            "body": textwrap.dedent("""\
                Hi {first_name},

                This is a friendly reminder that timesheets for the period ending
                {period_end} are due by {deadline}.

                Please ensure your hours are accurately recorded and submitted through
                the HR portal. Late submissions may affect payroll processing.

                If you have any questions about your timesheet, contact Payroll at
                payroll@{domain}.

                Many thanks,
                HR Operations
                {company}
            """),
            "attach_p": 0.10,
            "attach_types": ["xlsx"],
        },
        {
            "subject": "Benefits Open Enrollment — Closes {deadline}",
            "body": textwrap.dedent("""\
                Dear {first_name},

                Annual benefits open enrollment is now open and will close on {deadline}.

                This is your opportunity to:
                  • Review and update your health, dental, and vision coverage
                  • Adjust your FSA / HSA contributions
                  • Update dependants on your plan

                Please review the attached Benefits Guide for details on the options
                available to you this year. Log in to the benefits portal to make
                your selections before the deadline.

                If you miss the deadline, your current elections will roll over and
                you will not be able to make changes until next year's enrollment period.

                Human Resources
                {company}
            """),
            "attach_p": 0.85,
            "attach_types": ["pdf"],
        },
        {
            "subject": "Welcome to the Team — {new_hire} joins {department}!",
            "body": textwrap.dedent("""\
                Hi everyone,

                Please join me in welcoming {new_hire} who will be joining the
                {department} team as a {job_title} starting {start_date}.

                {new_hire} comes to us from {prev_company} with {years} years of
                experience in {field}. Please make them feel welcome!

                Best,
                {sender_first} {sender_last}
                Head of Human Resources
                {company}
            """),
            "attach_p": 0.05,
            "attach_types": [],
        },
        {
            "subject": "Performance Review Season — Please Complete Your Self-Assessment",
            "body": textwrap.dedent("""\
                Hi {first_name},

                It's that time of year again! Annual performance reviews are underway
                and we'd like you to complete your self-assessment by {deadline}.

                The self-assessment form is attached. Please:
                  1. Reflect on your achievements over the past year
                  2. List any challenges or areas for development
                  3. Set 3-5 goals for the coming year
                  4. Return the completed form to your manager

                Your manager will schedule a 1-on-1 meeting to discuss your review
                within the next two weeks.

                Thank you for your continued hard work and dedication.

                HR Team
                {company}
            """),
            "attach_p": 0.90,
            "attach_types": ["docx"],
        },
        {
            "subject": "Updated Employee Handbook — Please Read and Acknowledge",
            "body": textwrap.dedent("""\
                Dear {first_name},

                The {company} Employee Handbook has been updated effective {effective_date}.

                Key changes include:
                  • Remote work policy (Section 4.2)
                  • Travel and expense guidelines (Section 7.1)
                  • Code of conduct updates (Section 2)
                  • Updated PTO accrual schedule (Section 5.3)

                Please review the updated handbook attached to this email and sign the
                acknowledgement form in the HR portal by {deadline}.

                For questions, reach out to hr@{domain}.

                With thanks,
                Human Resources
                {company}
            """),
            "attach_p": 0.95,
            "attach_types": ["pdf"],
        },
    ],

    # ── Finance ──────────────────────────────────────────────────────────── #
    "finance": [
        {
            "subject": "Invoice #{inv_num} — {vendor} — ${amount}",
            "body": textwrap.dedent("""\
                Hi {first_name},

                Please find attached Invoice #{inv_num} from {vendor} for the amount
                of ${amount} due on {due_date}.

                Details:
                  Vendor       : {vendor}
                  Invoice #    : {inv_num}
                  Amount Due   : ${amount}
                  Payment Terms: Net {terms}
                  Due Date     : {due_date}

                Please review and process according to our standard AP procedures.
                If there are any discrepancies, contact the vendor directly and cc
                accounts.payable@{domain}.

                Regards,
                Accounts Payable
                {company}
            """),
            "attach_p": 0.95,
            "attach_types": ["pdf", "xlsx"],
        },
        {
            "subject": "Expense Report Reminder — Q{quarter} Submissions Due {deadline}",
            "body": textwrap.dedent("""\
                Dear {first_name},

                This is a reminder that Q{quarter} expense reports are due by {deadline}.

                Please submit all business expenses incurred between {period_start}
                and {period_end} through the expense management system.

                Required documentation:
                  • Original receipts for all expenses over ${receipt_threshold}
                  • Business justification for each expense
                  • Manager approval

                Late submissions cannot be guaranteed for inclusion in this period's
                payroll cycle.

                Finance Team
                {company}
            """),
            "attach_p": 0.35,
            "attach_types": ["xlsx"],
        },
        {
            "subject": "Purchase Order #{po_num} — Approved",
            "body": textwrap.dedent("""\
                Hi {first_name},

                Your purchase order #{po_num} has been approved by Finance.

                  PO Number   : {po_num}
                  Vendor      : {vendor}
                  Total Value : ${amount}
                  Cost Centre : {cost_centre}
                  Approved By : {approver}

                Please proceed with the purchase and ensure all receipts are saved
                for reconciliation. The PO is valid until {expiry}.

                For questions, contact procurement@{domain}.

                Finance & Procurement
                {company}
            """),
            "attach_p": 0.80,
            "attach_types": ["pdf"],
        },
    ],

    # ── Vendor / External ────────────────────────────────────────────────── #
    "vendor": [
        {
            "subject": "Your Order #{order_num} Has Shipped",
            "body": textwrap.dedent("""\
                Hi {first_name},

                Great news — your order #{order_num} has shipped!

                Shipping Details:
                  Order #         : {order_num}
                  Carrier         : {carrier}
                  Tracking Number : {tracking}
                  Estimated Delivery: {est_delivery}

                You can track your shipment at the carrier's website using the
                tracking number above.

                If you have any questions about your order, please contact our
                support team at support@{vendor_domain}.

                Thank you for your business!

                {vendor}
                Customer Service
            """),
            "attach_p": 0.20,
            "attach_types": ["pdf"],
        },
        {
            "subject": "Subscription Renewal — {product} — Due {due_date}",
            "body": textwrap.dedent("""\
                Dear {first_name},

                Your subscription to {product} is due for renewal on {due_date}.

                Plan         : {plan}
                Renewal Cost : ${amount}/year
                Account      : {email}

                Your subscription will auto-renew unless you take action. Please
                review the attached renewal invoice and ensure your payment details
                are up to date.

                To manage your subscription, log in to your account at {vendor}.

                Best,
                {vendor} Billing Team
            """),
            "attach_p": 0.70,
            "attach_types": ["pdf"],
        },
        {
            "subject": "[Ticket #{ticket}] Re: {issue_summary}",
            "body": textwrap.dedent("""\
                Hi {first_name},

                Thank you for contacting {vendor} Support.

                We have an update on your support ticket #{ticket} regarding:
                "{issue_summary}"

                Our engineering team has reviewed the issue and {resolution}.

                If this resolves your issue, no further action is needed and the
                ticket will be closed in 3 business days.

                If you are still experiencing the problem, please reply to this
                email with additional details.

                Support Team
                {vendor}
                support@{vendor_domain}
            """),
            "attach_p": 0.25,
            "attach_types": ["pdf", "xlsx"],
        },
    ],

    # ── Colleague ────────────────────────────────────────────────────────── #
    "colleague": [
        {
            "subject": "Quick question about the {project} project",
            "body": textwrap.dedent("""\
                Hey {first_name},

                Hope you're doing well. I had a quick question about the {project}
                project — specifically around the {component} implementation.

                Are you free for a quick 15-minute call this week to walk me through
                the approach? I want to make sure I'm aligned before I start working
                on my piece.

                Let me know what works for you.

                Thanks,
                {sender_first}
            """),
            "attach_p": 0.10,
            "attach_types": ["docx", "pdf"],
        },
        {
            "subject": "FYI: {topic}",
            "body": textwrap.dedent("""\
                Hi {first_name},

                Just wanted to share this with you — thought it might be useful for
                the work you're doing on {project}.

                The attached {doc_type} covers {topic} in some detail. Pay attention
                to section {section} in particular — it's directly relevant to our
                use case.

                No action needed from you, just keeping you in the loop.

                Cheers,
                {sender_first} {sender_last}
            """),
            "attach_p": 0.75,
            "attach_types": ["pdf", "docx", "xlsx"],
        },
        {
            "subject": "Can you review this before I send it out?",
            "body": textwrap.dedent("""\
                Hi {first_name},

                Would you mind taking a quick look at the attached {doc_type} before
                I send it to {audience}? I want to make sure it's accurate and that
                I haven't missed anything important.

                I'm hoping to send it by {send_by}, so if you could review it by
                {review_by} that would be great.

                Happy to return the favour — let me know!

                {sender_first}
            """),
            "attach_p": 0.99,
            "attach_types": ["docx", "pdf", "xlsx"],
        },
        {
            "subject": "Meeting notes — {meeting_topic} — {date}",
            "body": textwrap.dedent("""\
                Hi all,

                Please find below the notes from today's {meeting_topic} meeting.

                Attendees: {attendees}

                Key Discussion Points:
                  • {point_1}
                  • {point_2}
                  • {point_3}

                Action Items:
                  • {action_1} — Owner: {owner_1} — Due: {due_1}
                  • {action_2} — Owner: {owner_2} — Due: {due_2}

                Next meeting: {next_meeting}

                Notes attached. Please shout if I've missed anything.

                {sender_first} {sender_last}
            """),
            "attach_p": 0.80,
            "attach_types": ["docx", "pdf"],
        },
    ],

    # ── Management ───────────────────────────────────────────────────────── #
    "management": [
        {
            "subject": "All-Hands Meeting — {date} at {time}",
            "body": textwrap.dedent("""\
                Dear Team,

                You are invited to our quarterly all-hands meeting.

                  Date  : {date}
                  Time  : {time}
                  Venue : {venue}

                Agenda:
                  1. Q{quarter} Business Review — {exec1}
                  2. Product Roadmap Update — {exec2}
                  3. People & Culture Update — HR
                  4. Open Q&A

                A dial-in option will be available for remote staff. Details to follow.
                Please block your calendar. Attendance is expected for all staff.

                See you there,
                {sender_first} {sender_last}
                {title}
            """),
            "attach_p": 0.40,
            "attach_types": ["pdf"],
        },
        {
            "subject": "Q{quarter} Results Summary — {company}",
            "body": textwrap.dedent("""\
                Dear {first_name},

                Please find attached the Q{quarter} results summary for {company}.

                Highlights:
                  • Revenue: ${revenue}M ({revenue_delta}% vs prior quarter)
                  • Headcount: {headcount} ({headcount_delta})
                  • Key initiatives on track: {initiatives_ok}/{initiatives_total}

                Full details are in the attached report. This is confidential and
                for internal distribution only.

                Questions? Reach out to your manager or the Finance team.

                {sender_first} {sender_last}
                {title}, {company}
            """),
            "attach_p": 0.95,
            "attach_types": ["pdf", "xlsx"],
        },
    ],
}

# Category weights for random selection
CATEGORY_WEIGHTS = {
    "it": 20,
    "hr": 20,
    "finance": 15,
    "vendor": 20,
    "colleague": 15,
    "management": 10,
}


# --------------------------------------------------------------------------- #
# Context builder                                                               #
# --------------------------------------------------------------------------- #

def _future(days_min=1, days_max=30) -> str:
    d = datetime.now() + timedelta(days=random.randint(days_min, days_max))
    return d.strftime("%B %d, %Y")

def _past(days_min=1, days_max=30) -> str:
    d = datetime.now() - timedelta(days=random.randint(days_min, days_max))
    return d.strftime("%B %d, %Y")

def _version() -> str:
    return f"{random.randint(2,8)}.{random.randint(0,15)}.{random.randint(0,9)}"

def _make_ctx() -> dict:
    """Build a flat context dict with fake values for all template variables."""
    first = fk.first_name()
    last  = fk.last_name()
    company = fk.company().replace(",", "").replace(".", "")
    domain  = fk.domain_name()
    sender_first = fk.first_name()
    sender_last  = fk.last_name()
    quarter = random.choice([1, 2, 3, 4])
    period_end = _past(1, 14)
    period_start = _past(30, 90)

    projects = ["Phoenix", "Atlas", "Orion", "Aurora", "Nexus", "Horizon",
                "Titan", "Apex", "Vector", "Nova", "Synapse", "Catalyst"]
    components = ["authentication", "data pipeline", "API gateway", "caching layer",
                  "reporting module", "payment integration", "search service",
                  "notification system", "admin dashboard", "scheduling engine"]
    doc_types = ["report", "proposal", "analysis", "presentation", "brief",
                 "specification", "summary", "overview", "draft", "plan"]
    topics = ["market analysis", "Q{q} budget forecast".format(q=quarter),
              "competitor landscape", "technical architecture", "release plan",
              "security posture report", "vendor evaluation", "roadmap update"]
    resolutions = [
        "have identified the root cause and deployed a fix in v{v}".format(v=_version()),
        "are still investigating and will provide an update within 2 business days",
        "have escalated this to the engineering team for further review",
        "have reproduced the issue and a patch is scheduled for the next release",
    ]

    vendor = fk.company().replace(",", "").replace(".", "")
    rev = round(random.uniform(5, 500), 1)
    rev_delta = round(random.uniform(-15, 30), 1)

    return {
        "first_name":     first,
        "last_name":      last,
        "full_name":      f"{first} {last}",
        "email":          fk.email(),
        "company":        company,
        "domain":         domain,
        "ext":            str(random.randint(1000, 9999)),
        "sender_first":   sender_first,
        "sender_last":    sender_last,
        "sender_email":   fk.email(),
        "days":           str(random.randint(1, 14)),
        "expire_date":    _future(1, 14),
        "deadline":       _future(3, 21),
        "effective_date": _future(1, 30),
        "due_date":       _future(5, 45),
        "start_date":     _future(3, 30),
        "eol_date":       _future(30, 90),
        "review_by":      _future(1, 5),
        "send_by":        _future(2, 7),
        "system":         random.choice(["ERP System", "CRM Platform", "AD Domain Controllers",
                                          "Email Gateway", "VPN Concentrator", "File Server",
                                          "HR Portal", "Finance System"]),
        "maint_date":     _future(2, 14),
        "maint_time":     f"{random.randint(0,5):02d}:00",
        "duration":       str(random.randint(1, 6)),
        "impact":         random.choice(["Read-only access", "Full outage — no access",
                                          "Intermittent connectivity", "Degraded performance"]),
        "version":        _version(),
        "old_version":    _version(),
        "inv_num":        str(random.randint(10000, 99999)),
        "po_num":         f"PO-{random.randint(10000,99999)}",
        "amount":         f"{random.randint(200, 95000):,}",
        "terms":          str(random.choice([15, 30, 45, 60])),
        "vendor":         vendor,
        "vendor_domain":  fk.domain_name(),
        "approver":       f"{fk.first_name()} {fk.last_name()}",
        "cost_centre":    f"CC-{random.randint(1000,9999)}",
        "expiry":         _future(30, 180),
        "quarter":        str(quarter),
        "period_start":   period_start,
        "period_end":     period_end,
        "receipt_threshold": str(random.choice([25, 50, 75])),
        "order_num":      f"ORD-{random.randint(100000,999999)}",
        "carrier":        random.choice(["UPS", "FedEx", "DHL", "USPS", "OnTrac"]),
        "tracking":       fk.bothify(text="1Z###?##?######?##"),
        "est_delivery":   _future(1, 7),
        "product":        random.choice(["Microsoft 365", "Adobe Creative Cloud",
                                          "Zoom Business", "Slack Pro", "Jira Software",
                                          "Confluence", "GitHub Enterprise", "Datadog"]),
        "plan":           random.choice(["Business", "Professional", "Enterprise", "Team"]),
        "ticket":         str(random.randint(100000, 999999)),
        "issue_summary":  random.choice(["Login failure after password reset",
                                          "Report export timing out",
                                          "Sync not completing",
                                          "Performance degradation on large datasets",
                                          "Email notifications not sending"]),
        "resolution":     random.choice(resolutions),
        "project":        random.choice(projects),
        "component":      random.choice(components),
        "doc_type":       random.choice(doc_types),
        "topic":          random.choice(topics),
        "section":        f"{random.randint(2,8)}.{random.randint(1,5)}",
        "audience":       random.choice(["the leadership team", "the client",
                                          "the whole department", "the board"]),
        "meeting_topic":  random.choice(["Sprint Planning", "Architecture Review",
                                          "Budget Review", "Team Standup",
                                          "Product Roadmap", "Security Briefing"]),
        "date":           _future(3, 30),
        "time":           f"{random.randint(9,16)}:{random.choice(['00','15','30','45'])}",
        "venue":          random.choice(["Conference Room A", "Board Room", "Zoom",
                                          "Google Meet", "Main Auditorium"]),
        "exec1":          f"{fk.first_name()} {fk.last_name()}",
        "exec2":          f"{fk.first_name()} {fk.last_name()}",
        "title":          random.choice(["CEO", "CTO", "CFO", "VP Engineering",
                                          "Head of People Ops", "Director of Finance"]),
        "revenue":        str(rev),
        "revenue_delta":  f"{'+' if rev_delta >= 0 else ''}{rev_delta}",
        "headcount":      str(random.randint(50, 5000)),
        "headcount_delta": random.choice(["+12", "+5", "-3", "+28", "0"]),
        "initiatives_ok": str(random.randint(3, 8)),
        "initiatives_total": str(random.randint(8, 12)),
        "new_hire":       f"{fk.first_name()} {fk.last_name()}",
        "department":     random.choice(["Engineering", "Sales", "Marketing",
                                          "Finance", "HR", "Operations", "Legal"]),
        "job_title":      fk.job(),
        "prev_company":   fk.company().replace(",", ""),
        "years":          str(random.randint(2, 20)),
        "field":          random.choice(["software development", "data analytics",
                                          "project management", "sales", "finance",
                                          "cloud infrastructure", "cybersecurity"]),
        "attendees":      ", ".join([f"{fk.first_name()} {fk.last_name()}"
                                     for _ in range(random.randint(3, 7))]),
        "point_1":        random.choice(["Reviewed sprint progress and blockers",
                                          "Discussed Q3 budget variance",
                                          "Aligned on go-to-market timeline",
                                          "Reviewed security audit findings"]),
        "point_2":        random.choice(["Agreed on revised delivery date",
                                          "Escalated resource constraints to leadership",
                                          "Confirmed vendor selection",
                                          "Approved design mockups"]),
        "point_3":        random.choice(["Identified risks and mitigation steps",
                                          "Updated project RACI chart",
                                          "Reviewed customer feedback themes",
                                          "Agreed on testing strategy"]),
        "action_1":       random.choice(["Update project plan", "Send revised proposal",
                                          "Schedule follow-up call", "Prepare cost analysis"]),
        "owner_1":        f"{fk.first_name()} {fk.last_name()}",
        "due_1":          _future(3, 14),
        "action_2":       random.choice(["Review draft document", "Contact vendor",
                                          "Update stakeholders", "Prepare report"]),
        "owner_2":        f"{fk.first_name()} {fk.last_name()}",
        "due_2":          _future(7, 21),
        "next_meeting":   _future(7, 21),
    }


# --------------------------------------------------------------------------- #
# Public API                                                                    #
# --------------------------------------------------------------------------- #

def generate_email() -> dict:
    """
    Return a dict describing a generated email:
      sender_name, sender_email, subject, body,
      has_attachment (bool), attach_type (str|None), category (str)
    """
    categories = list(CATEGORY_WEIGHTS.keys())
    weights    = [CATEGORY_WEIGHTS[c] for c in categories]
    category   = random.choices(categories, weights=weights, k=1)[0]
    template   = random.choice(TEMPLATES[category])
    ctx        = _make_ctx()

    # Render subject and body (safe format — ignore unknown keys)
    try:
        subject = template["subject"].format_map(ctx)
    except (KeyError, IndexError):
        subject = template["subject"]

    try:
        body = template["body"].format_map(ctx)
    except (KeyError, IndexError):
        body = template["body"]

    has_attachment = random.random() < template["attach_p"]
    attach_type    = None
    if has_attachment and template["attach_types"]:
        attach_type = random.choice(template["attach_types"])

    # Build a realistic sender based on category
    if category in ("it",):
        sender_name  = f"IT Help Desk — {ctx['company']}"
        sender_email = f"helpdesk@{ctx['domain']}"
    elif category == "hr":
        sender_name  = f"HR Team — {ctx['company']}"
        sender_email = f"hr@{ctx['domain']}"
    elif category == "finance":
        sender_name  = f"Finance — {ctx['company']}"
        sender_email = f"finance@{ctx['domain']}"
    elif category == "vendor":
        sender_name  = ctx["vendor"]
        sender_email = f"noreply@{ctx['vendor_domain']}"
    elif category == "colleague":
        sender_name  = f"{ctx['sender_first']} {ctx['sender_last']}"
        sender_email = f"{ctx['sender_first'].lower()}.{ctx['sender_last'].lower()}@{ctx['domain']}"
    else:  # management
        sender_name  = f"{ctx['exec1']}"
        sender_email = f"{ctx['exec1'].split()[0].lower()}@{ctx['domain']}"

    return {
        "sender_name":   sender_name,
        "sender_email":  sender_email,
        "subject":       subject,
        "body":          body,
        "has_attachment": has_attachment,
        "attach_type":   attach_type,
        "category":      category,
    }
