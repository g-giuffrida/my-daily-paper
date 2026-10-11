"""Free, explicitly illustrative editorial proof: mixed columns, graphics and planner.

No API requests. All numbers below are labelled illustrative, not live reporting.
"""

from copy import deepcopy
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fitz
from engine import render_pdf, compose_regions, register_fonts, week_dates
from settings import DEFAULT
from layout import budgets


def proof():
    settings = deepcopy(DEFAULT)
    settings.update(
        name="The Daily Ledger",
        tagline="A considered view of a changing world.",
        margin_mm=10,
        gutter_mm=3,
        masthead_mm=42,
        headline_size=16,
        body_size=9,
        padding_mm=1,
        line_spacing=1.12,
        sources_visible=False,
    )
    names = [
        "Finance & markets",
        "Switzerland",
        "The daily cartoon",
        "The week ahead",
        "German notebook",
        "Economics explained",
        "AI engineering",
    ]
    settings["sections"] = [
        {
            "id": f"proof{i}",
            "name": name,
            "prompt": "Illustrative editorial proof, not live reporting.",
            "spaces": [2, 1, 1, 2, 2, 2, 2][i],
            "anchor": [0, 1, 3, 4, 6, 7, 10][i],
            "orientation": "Vertical" if i in (0, 4, 5) else "Horizontal",
        }
        for i, name in enumerate(names)
    ]
    p = lambda text: {"type": "paragraph", "text": text}
    h = lambda text: {"type": "heading", "text": text}
    copy = [
        (
            "Growth is not the same as value",
            [
                p(
                    "A company can sell more every year and still leave its owners worse off. The missing question is not whether revenue grew, but how much capital was needed to produce that growth. A new factory, a larger inventory and more generous customer credit all consume cash before the promised benefits arrive."
                ),
                p(
                    "Consider an illustrative business that invests 100 units and earns 12 units of annual operating profit after tax. Its return on invested capital is 12%. If investors require a 9% return for the risks involved, the operation creates an economic surplus of three units. Expanding that business on the same terms can create value; expanding at a 6% return cannot."
                ),
                h("Read the cash, not just the headline"),
                p(
                    "The distinction matters when comparing fast-growing companies. Reported earnings may improve while cash is tied up in customer balances or unfinished projects. Conversely, a temporary investment programme can depress current cash flow while laying the foundations for stronger future returns. Neither observation alone settles the investment case."
                ),
                {
                    "type": "chart",
                    "title": "Same capital, different outcomes",
                    "kind": "bar",
                    "labels": ["Required", "Business A", "Business B"],
                    "values": [9, 12, 6],
                    "unit": "illustrative return, %",
                },
                p(
                    "A useful reading habit is to compare management's growth promises with the reinvestment they require. Ask how much cash stays in the business, how long it is committed, and what evidence supports the expected return. The small comparison above is illustrative arithmetic, not a valuation of a listed company."
                ),
            ],
        ),
        (
            "Was e gueti Debatte bruucht",
            [
                p(
                    "E politischi Schlagziile seit no nöd, was en Vorschlag im Alltag verändert. Entscheidend sind d'Frag, wer zahlt, wer profitiert und weli Alternative zur Wahl staht. Die drü Frage helfed, au komplizierti Wirtschaftsdebatte nüchtern z'läse."
                ),
                p(
                    "Bi ere neue Regel lohnt sich en Blick uf d'Umsetzig: Wer kontrolliert sie? Wie viel Ufwand entsteht? Und woran würd mer erkenne, ob sie funktioniert? E gueti Begründig nennt nöd nume es Ziel, sondern au d'Abwägige."
                ),
                p(
                    "Das isch en illustrative Sprach- und Layouttest, kei aktuelli Nachricht. I de echte Usgab ghöred verifizierti Quelle und s'Publikationsdatum dezue."
                ),
            ],
        ),
        (
            "Effizienz, ganz gründlich",
            [
                {
                    "type": "diagram",
                    "title": "D'Büro-Logik",
                    "steps": [
                        "Sitzig plane",
                        "Über weniger Sitzige rede",
                        "Folgesitzig buche",
                    ],
                    "caption": "Illustrative satirical diagram · no image-model call.",
                },
                p(
                    "«Mir hend d'Ziitverschwendig jetzt wenigstens sauber protokolliert.»"
                ),
            ],
        ),
        (
            "A week with room to think",
            [
                {
                    "type": "calendar",
                    "days": [
                        {"date": d, "events": events}
                        for d, events in zip(
                            week_dates("2026-10-14"),
                            [
                                ["Office · project review", "Gym"],
                                ["Home · focused writing", "Language practice"],
                                ["Office · team discussion", "Dinner with a friend"],
                                ["Office · finish proposal", "Gym"],
                                ["Home · research and weekly review"],
                                ["Groceries", "Read and relax"],
                                ["Walk outdoors", "Plan next week"],
                            ],
                        )
                    ],
                },
                p("DAILY HABITS  □ German practice   □ Study   □ Exercise"),
                p(
                    "WEEKLY PRIORITIES  □ Complete proposal   □ Review priorities   □ Protect one quiet morning"
                ),
            ],
        ),
        (
            "Although, because and therefore",
            [
                p(
                    "At B1 level, connecting ideas is often more useful than collecting new nouns. Three German words let you explain a reason, acknowledge a contrast and describe a consequence: weil, obwohl and deshalb. The important difference is where the verb goes."
                ),
                h("Give a reason: weil"),
                p(
                    "Weil introduces a subordinate clause, so its conjugated verb moves to the end. Compare: Ich bleibe zu Hause. Ich bin müde. Together they become Ich bleibe zu Hause, weil ich müde bin. In English: I am staying at home because I am tired. Notice that bin, not müde, finishes the clause."
                ),
                h("Allow a contrast: obwohl"),
                p(
                    "Obwohl means although and follows the same verb-final pattern: Ich gehe spazieren, obwohl es regnet. You are going for a walk despite the rain. You can place that clause first: Obwohl es regnet, gehe ich spazieren. The entire opening clause occupies the first position; gehe therefore comes immediately after the comma."
                ),
                h("Show a result: deshalb"),
                p(
                    "Deshalb means therefore. It connects two main clauses rather than introducing a subordinate one: Es regnet. Deshalb nehme ich einen Schirm mit. The conjugated verb nehme stays in second position. The separable prefix mit comes at the end, just as it does in an ordinary main clause."
                ),
                p(
                    "Practise with two facts: Der Zug hat Verspätung. Ich komme später. Try a reason with weil and a consequence with deshalb. Answers: Ich komme später, weil der Zug Verspätung hat. Der Zug hat Verspätung. Deshalb komme ich später. The meaning is similar; the grammatical structure is different."
                ),
            ],
        ),
        (
            "Why a bond's price moves",
            [
                p(
                    "A fixed-rate bond promises cash on specified dates. Its market price is what investors will pay today for those future payments. When the return available on comparable new investments rises, the old bond's unchanged payments become less attractive. Its price must fall until its prospective return is competitive."
                ),
                h("Start with one payment"),
                p(
                    "Imagine an illustrative bond that pays 100 units in one year and nothing before then. If the required annual return is 5%, its present value is 100 divided by 1.05, or about 95.24. If that required return rises to 6%, the value falls to about 94.34. The issuer has not changed the promised payment; the discount rate has changed."
                ),
                p(
                    "A bond with several coupon payments is the sum of several calculations of that kind. Each payment is discounted for the time until it arrives. Cash received further in the future is generally more sensitive to a change in the discount rate. This is the intuition behind duration, a measure of interest-rate sensitivity."
                ),
                h("Do not confuse price and certainty"),
                p(
                    "Interest rates are not the only influence. A deterioration in the issuer's creditworthiness can increase the return investors demand. Thin trading can also make a security harder to sell at a predictable price. A bond fund does not necessarily behave like an individual bond held until maturity because its portfolio changes over time."
                ),
                p(
                    "The useful lesson is to ask which risk explains a price movement. Has the general level of rates changed, has the issuer become riskier, or has liquidity deteriorated? The arithmetic here is illustrative and deliberately simple, but it separates the promised cash flows from the price paid to receive them."
                ),
            ],
        ),
        (
            "A reliable agent knows when to stop",
            [
                p(
                    "A language model can propose a useful next action, but an application still needs to decide whether that action is permitted and whether another step is worth taking. A small state machine makes those decisions explicit. It records what the system is doing, what evidence it has, and which transitions are allowed."
                ),
                {
                    "type": "diagram",
                    "title": "A bounded research workflow",
                    "steps": [
                        "Retrieve evidence",
                        "Draft answer",
                        "Validate citations",
                        "Deliver or revise",
                    ],
                    "caption": "Application-controlled transitions; at most one revision in this example.",
                },
                p(
                    "For a financial-statement assistant, retrieval might return passages with stable document identifiers. Drafting can reference only those identifiers. Validation then checks that every reference exists and that required fields are present. A failed check routes the draft to revision; an exhausted retry budget routes it to a clear, inspectable failure rather than an endless loop."
                ),
                h("Keep the machinery proportionate"),
                p(
                    "A plain Python function with an explicit state object is enough for many workflows. A graph framework becomes useful when there are several branches, persisted checkpoints or human approval steps. It does not make the model's reasoning true. Grounding, permission checks and evaluation remain application responsibilities."
                ),
                p(
                    "Record the state transition, not just the final answer. That gives you a way to distinguish retrieval failures from drafting failures and to measure whether an extra model call actually improves the result. The engineering principle is simple: let the model suggest work, but let trusted code own the boundaries."
                ),
            ],
        ),
    ]
    issue = {
        "day": "2026-10-14",
        "timezone": settings["timezone"],
        "sample": True,
        "images": {},
        "sections": [
            {
                "id": f"proof{i}",
                "headline": title,
                "summary": "Illustrative editorial proof.",
                "blocks": blocks,
                "sources": [],
            }
            for i, (title, blocks) in enumerate(copy)
        ],
    }
    return settings, issue


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    settings, issue = proof()
    register_fonts()
    regions, placements = compose_regions(settings, issue)
    pdf = render_pdf(settings, issue)
    (args.directory / "editorial-proof.pdf").write_bytes(pdf)
    doc = fitz.open(stream=pdf, filetype="pdf")
    assert len(doc) == 2
    for n, page in enumerate(doc, 1):
        page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(
            str(args.directory / f"editorial-proof-{n}.png")
        )
    report = {
        "pages": len(doc),
        "budgets": budgets(settings),
        "placements": len(placements),
    }
    (args.directory / "editorial-proof-report.json").write_text(
        json.dumps(report, indent=2)
    )
    print("Two-page illustrative proof rendered; no model calls.")
