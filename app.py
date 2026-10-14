import html
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from supabase import create_client


# ------------------------------------------------------------
# PAGE
# ------------------------------------------------------------
st.set_page_config(
    page_title="DIFFUSION AX CONTEST",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ------------------------------------------------------------
# USERS
# ------------------------------------------------------------
USERS = {
    "DRAM_ALD": {"password": "1026", "role": "judge", "weight": 1},
    "DRAM_FUR": {"password": "2026", "role": "judge", "weight": 1},
    "DRAM_IMP": {"password": "3026", "role": "judge", "weight": 1},
    "NAND_ALD": {"password": "4026", "role": "judge", "weight": 1},
    "NAND_FUR": {"password": "5026", "role": "judge", "weight": 1},
    "NAND_IMP": {"password": "6026", "role": "judge", "weight": 1},
    "M15X_DIFF": {"password": "7026", "role": "judge", "weight": 1},
    "DIFF_STRAT": {"password": "8026", "role": "judge", "weight": 1},
    "DIFF_CHAMPION": {"password": "9026", "role": "judge", "weight": 3},
    "MASTER": {"password": "2006", "role": "admin", "weight": 0},
}

# 제출현황 / 코멘트 정렬 순서
JUDGES = [
    "DIFF_CHAMPION",
    "DIFF_STRAT",
    "DRAM_ALD",
    "DRAM_FUR",
    "DRAM_IMP",
    "M15X_DIFF",
    "NAND_ALD",
    "NAND_FUR",
    "NAND_IMP",
]

JUDGE_ORDER = {name: i for i, name in enumerate(JUDGES)}

MAX_TOTAL = 25 * sum(USERS[u]["weight"] for u in JUDGES)

CRITERIA = [
    (
        "현업 문제 해결성",
        "실제 현장의 Pain Point / Needs를 제대로 해결하는가?",
    ),
    (
        "업무 효과",
        "시간 단축 · 품질 향상 · Risk 감소 등 효과가 명확한가?",
    ),
    (
        "Agent 완성도",
        "정확성 · 신뢰성이 실제 업무 활용 가능한 수준인가?",
    ),
    (
        "활용 편의성",
        "쉽게 사용 가능하며 Legacy System / Data와 잘 연결되는가?",
    ),
    (
        "확산 가능성",
        "다른 공정 · 팀에도 Skill / Tool / Agent 형태로 확산 가능한가?",
    ),
]


# ------------------------------------------------------------
# DB
# ------------------------------------------------------------
@st.cache_resource
def get_db():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


db = get_db()


def get_agents():
    rows = (
        db.table("agents")
        .select("slot,name,team,presenter,title")
        .order("slot")
        .execute()
        .data
        or []
    )

    by_slot = {int(r["slot"]): r for r in rows}

    result = []

    for slot in range(1, 6):
        r = by_slot.get(slot, {})

        result.append(
            {
                "slot": slot,
                "name": (
                    r.get("name")
                    or f"Agent {slot}"
                ).strip(),
                "team": (
                    r.get("team")
                    or ""
                ).strip(),
                "presenter": (
                    r.get("presenter")
                    or ""
                ).strip(),
                "title": (
                    r.get("title")
                    or ""
                ).strip(),
            }
        )

    return result


def get_all_scores():
    return (
        db.table("scores")
        .select("*")
        .execute()
        .data
        or []
    )


def get_score(judge, slot):
    rows = (
        db.table("scores")
        .select("*")
        .eq("judge", judge)
        .eq("agent_slot", slot)
        .execute()
        .data
        or []
    )

    return rows[0] if rows else None


def save_score(
    judge,
    slot,
    values,
    comment,
):
    weight = USERS[judge]["weight"]
    total = sum(values)

    db.table("scores").upsert(
        {
            "judge": judge,
            "agent_slot": slot,
            "c1": values[0],
            "c2": values[1],
            "c3": values[2],
            "c4": values[3],
            "c5": values[4],
            "total": total,
            "weight": weight,
            "weighted_total": total * weight,
            "comment": comment.strip(),
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        },
        on_conflict="judge,agent_slot",
    ).execute()


def update_agent(
    slot,
    name,
    team,
    presenter,
    title,
):
    db.table("agents").upsert(
        {
            "slot": slot,
            "name": (
                name or ""
            ).strip()
            or f"Agent {slot}",
            "team": (
                team or ""
            ).strip(),
            "presenter": (
                presenter or ""
            ).strip(),
            "title": (
                title or ""
            ).strip(),
        },
        on_conflict="slot",
    ).execute()


def clear_all_scores():
    (
        db.table("scores")
        .delete()
        .neq("judge", "__never__")
        .execute()
    )


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def esc(value):
    return html.escape(
        str(value or "")
    )


def logout():
    st.session_state.clear()
    st.rerun()


def show_value(
    value,
    fallback="",
):
    value = str(
        value or ""
    ).strip()

    return (
        value
        if value
        else fallback
    )


def agent_display_title(agent):
    return show_value(
        agent.get("title"),
        f"Agent {agent['slot']}",
    )


def build_aggregate():

    agents = get_agents()

    score_df = pd.DataFrame(
        get_all_scores()
    )

    base = pd.DataFrame(
        {
            "slot": [
                a["slot"]
                for a in agents
            ],
            "Agent": [
                a["name"]
                for a in agents
            ],
            "팀": [
                a["team"]
                for a in agents
            ],
            "발표자": [
                a["presenter"]
                for a in agents
            ],
            "제목": [
                a["title"]
                for a in agents
            ],
        }
    )

    if score_df.empty:

        for col in [
            "현업문제",
            "업무효과",
            "완성도",
            "활용편의",
            "확산가능",
            "최종점수",
            "제출인원",
        ]:
            base[col] = 0

        return (
            base,
            score_df,
        )

    for i in range(
        1,
        6,
    ):
        score_df[
            f"wc{i}"
        ] = (
            score_df[f"c{i}"]
            * score_df["weight"]
        )

    agg = (
        score_df
        .groupby(
            "agent_slot",
            as_index=False,
        )
        .agg(
            현업문제=(
                "wc1",
                "sum",
            ),
            업무효과=(
                "wc2",
                "sum",
            ),
            완성도=(
                "wc3",
                "sum",
            ),
            활용편의=(
                "wc4",
                "sum",
            ),
            확산가능=(
                "wc5",
                "sum",
            ),
            최종점수=(
                "weighted_total",
                "sum",
            ),
            제출인원=(
                "judge",
                "nunique",
            ),
        )
    )

    out = base.merge(
        agg,
        left_on="slot",
        right_on="agent_slot",
        how="left",
    )

    out = (
        out
        .drop(
            columns=[
                "agent_slot"
            ],
            errors="ignore",
        )
        .fillna(0)
    )

    numeric = [
        "현업문제",
        "업무효과",
        "완성도",
        "활용편의",
        "확산가능",
        "최종점수",
        "제출인원",
    ]

    out[numeric] = (
        out[numeric]
        .astype(int)
    )

    return (
        out,
        score_df,
    )


# ------------------------------------------------------------
# GLOBAL STYLE
# ------------------------------------------------------------
st.markdown(
    """
<style>

:root {

    --bg: #04101f;

    --panel:
        rgba(
            8,
            24,
            45,
            .88
        );

    --panel2:
        rgba(
            14,
            34,
            61,
            .78
        );

    --line:
        rgba(
            133,
            174,
            226,
            .18
        );

    --text: #f5f7fb;

    --muted: #9fb1c9;

    --blue: #70a7ff;

    --gold1: #fff0a8;

    --gold2: #d79a16;

    --silver1: #f5f7fa;

    --silver2: #8b98aa;

    --bronze1: #f4c08a;

    --bronze2: #9a4f1b;
}


html,
body,
[data-testid="stAppViewContainer"] {

    background:

        radial-gradient(
            circle at 50% -10%,
            rgba(
                62,
                113,
                184,
                .18
            ),
            transparent 38%
        ),

        linear-gradient(
            180deg,
            #051426 0%,
            #03101d 60%,
            #020b14 100%
        );

    color: var(--text);
}


[data-testid="stHeader"] {

    background:
        rgba(
            2,
            10,
            20,
            .70
        );

    backdrop-filter:
        blur(10px);
}


.block-container {

    max-width:
        1500px;

    padding-top:
        .8rem;

    padding-bottom:
        3rem;
}


div[data-testid="stTabs"] button {

    font-weight:
        800;

    font-size:
        1rem;
}


div[data-testid="stMetric"] {

    border:
        1px solid
        var(--line);

    background:
        rgba(
            12,
            30,
            54,
            .60
        );

    padding:
        12px 14px;

    border-radius:
        16px;
}


.stButton button,
.stDownloadButton button {

    min-height:
        46px;

    border-radius:
        12px;

    font-weight:
        800;
}


/* ==========================================================
   TOP BRAND
   ========================================================== */

.brandbar {

    display:
        flex;

    align-items:
        center;

    justify-content:
        space-between;

    gap:
        18px;

    padding:
        13px 18px;

    margin:
        0 0 14px 0;

    border:
        1px solid
        var(--line);

    border-radius:
        16px;

    background:
        linear-gradient(
            90deg,
            rgba(
                8,
                28,
                52,
                .97
            ),
            rgba(
                4,
                17,
                32,
                .92
            )
        );

    box-shadow:
        0 12px 30px
        rgba(
            0,
            0,
            0,
            .22
        );
}


.brand-left {

    display:
        flex;

    align-items:
        center;

    gap:
        10px;

    min-width:
        0;
}


.brand-main {

    font-size:
        1.28rem;

    font-weight:
        950;

    letter-spacing:
        .02em;

    white-space:
        nowrap;
}


.brand-main span {

    color:
        #78a7ff;
}


.brand-chip {

    font-size:
        .72rem;

    font-weight:
        900;

    padding:
        3px 8px;

    border-radius:
        8px;

    background:
        linear-gradient(
            135deg,
            #4778ff,
            #7e55ff
        );

    color:
        white;
}


.brand-user {

    color:
        var(--muted);

    font-size:
        .9rem;

    white-space:
        nowrap;
}


/* ==========================================================
   LOGIN / JUDGE CARD
   ========================================================== */

.glass-card {

    border:
        1px solid
        var(--line);

    border-radius:
        18px;

    padding:
        18px;

    background:
        linear-gradient(
            180deg,
            rgba(
                13,
                34,
                61,
                .90
            ),
            rgba(
                5,
                18,
                34,
                .90
            )
        );

    box-shadow:
        0 18px 45px
        rgba(
            0,
            0,
            0,
            .25
        );
}


.agent-card {

    border:
        1px solid
        rgba(
            92,
            147,
            220,
            .28
        );

    border-radius:
        18px;

    padding:
        16px 18px;

    margin:
        8px 0 16px 0;

    background:
        linear-gradient(
            135deg,
            rgba(
                18,
                47,
                82,
                .92
            ),
            rgba(
                8,
                26,
                49,
                .92
            )
        );
}


.agent-card-title {

    font-size:
        1.22rem;

    font-weight:
        950;

    line-height:
        1.35;
}


.agent-card-meta {

    display:
        flex;

    gap:
        18px;

    flex-wrap:
        wrap;

    margin-top:
        9px;

    color:
        #b9c8da;
}


.agent-card-meta b {

    color:
        #fff;
}


/* ==========================================================
   AWARDS STAGE
   ========================================================== */

.awards-stage {

    position:
        relative;

    overflow:
        hidden;

    border:
        1px solid
        rgba(
            216,
            168,
            59,
            .24
        );

    border-radius:
        26px;

    padding:
        28px 22px 22px 22px;

    margin:
        18px 0 24px 0;

    background:

        radial-gradient(
            ellipse at 18% 0%,
            rgba(
                255,
                232,
                170,
                .17
            ),
            transparent 26%
        ),

        radial-gradient(
            ellipse at 82% 0%,
            rgba(
                255,
                232,
                170,
                .14
            ),
            transparent 26%
        ),

        radial-gradient(
            ellipse at 50% 8%,
            rgba(
                99,
                152,
                255,
                .15
            ),
            transparent 30%
        ),

        linear-gradient(
            180deg,
            #071629 0%,
            #06111f 68%,
            #030913 100%
        );

    box-shadow:

        0 30px 65px
        rgba(
            0,
            0,
            0,
            .40
        ),

        inset 0 1px
        rgba(
            255,
            255,
            255,
            .06
        );
}


.awards-stage:before,
.awards-stage:after {

    content:
        "";

    position:
        absolute;

    top:
        -120px;

    width:
        160px;

    height:
        520px;

    background:
        linear-gradient(
            180deg,
            rgba(
                255,
                243,
                200,
                .26
            ),
            rgba(
                255,
                243,
                200,
                0
            )
        );

    filter:
        blur(12px);

    transform:
        rotate(14deg);

    pointer-events:
        none;
}


.awards-stage:before {

    left:
        8%;
}


.awards-stage:after {

    right:
        8%;

    transform:
        rotate(-14deg);
}


.awards-kicker {

    text-align:
        center;

    color:
        #c8d4e5;

    font-size:
        .82rem;

    font-weight:
        900;

    letter-spacing:
        .20em;
}


.awards-title {

    position:
        relative;

    z-index:
        2;

    text-align:
        center;

    font-weight:
        1000;

    font-size:
        clamp(
            1.65rem,
            3.8vw,
            2.8rem
        );

    letter-spacing:
        .03em;

    line-height:
        1.05;

    margin:
        5px 0 4px 0;

    color:
        #fff;

    text-shadow:
        0 6px 22px
        rgba(
            0,
            0,
            0,
            .35
        );
}


.awards-title .goldword {

    display:
        block;

    font-size:
        1.28em;

    background:
        linear-gradient(
            180deg,
            #fff3b0 0%,
            #f0bb46 42%,
            #b66c08 100%
        );

    -webkit-background-clip:
        text;

    -webkit-text-fill-color:
        transparent;
}


.awards-sub {

    position:
        relative;

    z-index:
        2;

    text-align:
        center;

    color:
        #b6c3d5;

    font-size:
        .92rem;

    margin-bottom:
        26px;
}


.podium-wrap {

    position:
        relative;

    z-index:
        2;

    display:
        grid;

    grid-template-columns:
        1fr 1.12fr 1fr;

    gap:
        14px;

    align-items:
        end;

    max-width:
        1200px;

    margin:
        0 auto;
}


.award-col {

    min-width:
        0;

    text-align:
        center;
}


.award-head {

    display:
        flex;

    justify-content:
        center;

    align-items:
        center;

    gap:
        8px;

    margin-bottom:
        10px;

    font-weight:
        950;
}


.medal {

    font-size:
        1.8rem;
}


.award-name {

    font-size:
        clamp(
            1rem,
            2vw,
            1.35rem
        );
}


.person-grid {

    display:
        grid;

    grid-template-columns:
        repeat(
            2,
            minmax(
                0,
                1fr
            )
        );

    gap:
        10px;

    align-items:
        stretch;
}


.gold .person-grid {

    grid-template-columns:
        1fr;
}


.person-card {

    min-height:
        118px;

    display:
        flex;

    flex-direction:
        column;

    justify-content:
        center;

    padding:
        13px 10px;

    border-radius:
        15px;

    background:
        linear-gradient(
            180deg,
            rgba(
                248,
                250,
                255,
                .97
            ),
            rgba(
                215,
                226,
                240,
                .96
            )
        );

    color:
        #0b1727;

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            .75
        );

    box-shadow:
        0 10px 24px
        rgba(
            0,
            0,
            0,
            .28
        );
}


.gold .person-card {

    border:
        2px solid
        #f4c85a;

    box-shadow:

        0 0 0 1px
        rgba(
            255,
            220,
            115,
            .18
        ),

        0 0 28px
        rgba(
            245,
            177,
            35,
            .30
        ),

        0 14px 32px
        rgba(
            0,
            0,
            0,
            .34
        );
}


.bronze .person-card {

    border-color:
        rgba(
            244,
            177,
            112,
            .8
        );
}


.silver .person-card {

    border-color:
        rgba(
            225,
            233,
            244,
            .9
        );
}


.person-team {

    font-size:
        1rem;

    font-weight:
        1000;

    line-height:
        1.2;

    overflow-wrap:
        anywhere;
}


.person-presenter {

    margin-top:
        5px;

    font-size:
        .88rem;

    font-weight:
        800;
}


.person-title {

    margin-top:
        6px;

    font-size:
        .76rem;

    line-height:
        1.35;

    color:
        #4d5d70;

    word-break:
        keep-all;
}


.person-empty {

    opacity:
        .55;
}


.podium-base {

    position:
        relative;

    margin-top:
        9px;

    border-radius:
        18px 18px 7px 7px;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    font-weight:
        1000;

    text-shadow:
        0 2px 8px
        rgba(
            0,
            0,
            0,
            .35
        );

    box-shadow:

        inset 0 1px
        rgba(
            255,
            255,
            255,
            .32
        ),

        0 16px 28px
        rgba(
            0,
            0,
            0,
            .28
        );
}


.podium-base span {

    font-size:
        2.2rem;
}


.silver .podium-base {

    height:
        78px;

    color:
        #f7fbff;

    background:
        linear-gradient(
            180deg,
            #aeb9c7 0%,
            #778496 48%,
            #465366 100%
        );
}


.gold .podium-base {

    height:
        112px;

    color:
        #fff8cf;

    background:
        linear-gradient(
            180deg,
            #e8b52e 0%,
            #b77408 48%,
            #7d4700 100%
        );

    box-shadow:

        0 0 34px
        rgba(
            234,
            175,
            41,
            .25
        ),

        inset 0 1px
        rgba(
            255,
            255,
            255,
            .4
        ),

        0 18px 34px
        rgba(
            0,
            0,
            0,
            .34
        );
}


.bronze .podium-base {

    height:
        62px;

    color:
        #ffe6ca;

    background:
        linear-gradient(
            180deg,
            #c4793e 0%,
            #8d481c 50%,
            #593016 100%
        );
}


/* ==========================================================
   SECTION
   ========================================================== */

.section-card {

    border:
        1px solid
        var(--line);

    border-radius:
        18px;

    padding:
        15px 16px;

    margin:
        14px 0;

    background:
        linear-gradient(
            180deg,
            rgba(
                9,
                27,
                50,
                .90
            ),
            rgba(
                4,
                16,
                31,
                .92
            )
        );
}


.section-title {

    font-size:
        1.15rem;

    font-weight:
        950;

    margin-bottom:
        10px;
}


.section-title small {

    font-size:
        .75rem;

    color:
        var(--muted);

    font-weight:
        600;

    margin-left:
        8px;
}


/* ==========================================================
   RESULT TABLE
   ========================================================== */

.table-scroll {

    overflow-x:
        auto;

    border:
        1px solid
        var(--line);

    border-radius:
        14px;
}


.ax-table {

    width:
        100%;

    min-width:
        1000px;

    border-collapse:
        collapse;

    background:
        rgba(
            4,
            16,
            30,
            .78
        );
}


.ax-table th {

    padding:
        11px 9px;

    text-align:
        center;

    font-size:
        .78rem;

    color:
        #d5e2f1;

    background:
        rgba(
            19,
            45,
            76,
            .88
        );

    border-bottom:
        1px solid
        var(--line);
}


.ax-table td {

    padding:
        11px 9px;

    text-align:
        center;

    font-size:
        .84rem;

    color:
        #eef4fb;

    border-bottom:
        1px solid
        rgba(
            133,
            174,
            226,
            .10
        );
}


.ax-table tr:first-child td {

    background:
        linear-gradient(
            90deg,
            rgba(
                201,
                145,
                20,
                .12
            ),
            rgba(
                201,
                145,
                20,
                .03
            )
        );
}


.rank-badge {

    display:
        inline-flex;

    width:
        30px;

    height:
        30px;

    align-items:
        center;

    justify-content:
        center;

    border-radius:
        50%;

    font-weight:
        1000;

    background:
        #1a2f49;

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            .15
        );
}


.r1 {

    background:
        linear-gradient(
            135deg,
            #ffe487,
            #c98a0d
        );

    color:
        #281700;
}


.r2 {

    background:
        linear-gradient(
            135deg,
            #edf2f7,
            #8794a6
        );

    color:
        #15202c;
}


.r3 {

    background:
        linear-gradient(
            135deg,
            #e7a56f,
            #8d4b24
        );

    color:
        #211007;
}


.team-bold {

    font-weight:
        950;
}


.title-left {

    text-align:
        left !important;

    max-width:
        320px;
}


/* ==========================================================
   COMMENTS
   ========================================================== */

.comments-grid {

    display:
        grid;

    grid-template-columns:
        repeat(
            3,
            minmax(
                0,
                1fr
            )
        );

    gap:
        11px;
}


.comment-card {

    border:
        1px solid
        rgba(
            116,
            159,
            216,
            .18
        );

    border-radius:
        15px;

    padding:
        13px 14px;

    background:
        linear-gradient(
            180deg,
            rgba(
                12,
                31,
                55,
                .88
            ),
            rgba(
                6,
                20,
                37,
                .88
            )
        );

    min-height:
        120px;
}


.comment-card.champion {

    border-color:
        rgba(
            239,
            190,
            62,
            .52
        );

    box-shadow:
        inset 0 0 0 1px
        rgba(
            239,
            190,
            62,
            .09
        );
}


.comment-top {

    display:
        flex;

    justify-content:
        space-between;

    gap:
        8px;

    align-items:
        flex-start;

    margin-bottom:
        8px;
}


.comment-judge {

    font-weight:
        950;

    color:
        #9fc0ff;

    overflow-wrap:
        anywhere;
}


.comment-card.champion
.comment-judge {

    color:
        #ffd76a;
}


.comment-agent {

    font-size:
        .72rem;

    color:
        #91a3ba;

    text-align:
        right;
}


.comment-body {

    font-size:
        .90rem;

    line-height:
        1.50;

    color:
        #edf3fa;

    word-break:
        keep-all;
}


.comment-score {

    margin-top:
        10px;

    font-size:
        .70rem;

    color:
        #7f93ad;
}


/* ==========================================================
   SETTINGS
   ========================================================== */

.agent-setting {

    border:
        1px solid
        var(--line);

    border-radius:
        16px;

    padding:
        12px 14px 2px 14px;

    margin-bottom:
        12px;

    background:
        rgba(
            8,
            24,
            45,
            .64
        );
}


/* ==========================================================
   TABLET
   ========================================================== */

@media (max-width: 900px) {

    .block-container {

        padding-left:
            .75rem;

        padding-right:
            .75rem;
    }


    .brand-user {

        display:
            none;
    }


    .podium-wrap {

        grid-template-columns:
            1fr 1.08fr 1fr;

        gap:
            7px;
    }


    .person-grid {

        grid-template-columns:
            1fr;

        gap:
            6px;
    }


    .person-card {

        min-height:
            106px;

        padding:
            10px 6px;
    }


    .person-team {

        font-size:
            .83rem;
    }


    .person-presenter {

        font-size:
            .74rem;
    }


    .person-title {

        font-size:
            .66rem;
    }


    .award-head {

        gap:
            4px;
    }


    .medal {

        font-size:
            1.45rem;
    }


    .awards-stage {

        padding:
            22px 8px 14px 8px;
    }


    .silver .podium-base {

        height:
            62px;
    }


    .gold .podium-base {

        height:
            88px;
    }


    .bronze .podium-base {

        height:
            50px;
    }


    .podium-base span {

        font-size:
            1.7rem;
    }


    .comments-grid {

        grid-template-columns:
            1fr;
    }
}


/* ==========================================================
   PHONE
   ========================================================== */

@media (max-width: 520px) {

    .brandbar {

        padding:
            11px 12px;
    }


    .brand-main {

        font-size:
            1.0rem;
    }


    .brand-chip {

        font-size:
            .62rem;
    }


    .awards-kicker {

        font-size:
            .67rem;
    }


    .awards-title {

        font-size:
            1.45rem;
    }


    .awards-sub {

        font-size:
            .76rem;

        margin-bottom:
            18px;
    }


    .award-name {

        font-size:
            .82rem;
    }


    .person-card {

        min-height:
            94px;
    }


    .person-team {

        font-size:
            .73rem;
    }


    .person-presenter {

        font-size:
            .67rem;
    }


    .person-title {

        font-size:
            .59rem;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# UI RENDERERS
# ------------------------------------------------------------
def render_brand(user=None):

    if user:

        who = (
            f"접속자 · {esc(user)}"
        )

    else:

        who = (
            "모바일 실시간 채점 시스템"
        )

    st.markdown(
        f"""
        <div class="brandbar">

            <div class="brand-left">

                <div class="brand-main">
                    DIFFUSION
                    <span>AX</span>
                    CONTEST
                </div>

                <div class="brand-chip">
                    AIX
                </div>

            </div>

            <div class="brand-user">
                {who}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


def render_agent_card(agent):

    title = esc(
        agent_display_title(
            agent
        )
    )

    team = esc(
        show_value(
            agent.get("team"),
            "팀 미입력",
        )
    )

    presenter = esc(
        show_value(
            agent.get("presenter"),
            "발표자 미입력",
        )
    )

    st.markdown(
        f"""
        <div class="agent-card">

            <div class="agent-card-title">
                {title}
            </div>

            <div class="agent-card-meta">

                <span>
                    <b>팀</b>
                    {team}
                </span>

                <span>
                    <b>발표자</b>
                    {presenter}
                </span>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


def person_card(
    row,
):

    if not row:

        return """
        <div class="person-card person-empty">

            <div class="person-team">
                &nbsp;
            </div>

            <div class="person-presenter">
                &nbsp;
            </div>

            <div class="person-title">
                &nbsp;
            </div>

        </div>
        """

    team = esc(
        show_value(
            row.get("팀"),
            "",
        )
    )

    presenter = esc(
        show_value(
            row.get("발표자"),
            "",
        )
    )

    title = esc(
        show_value(
            row.get("제목"),
            "",
        )
    )

    return f"""
    <div class="person-card">

        <div class="person-team">
            {team}
        </div>

        <div class="person-presenter">
            {presenter}
        </div>

        <div class="person-title">
            {title}
        </div>

    </div>
    """


def render_awards_stage(result):

    rows = result.to_dict(
        "records"
    )

    first = (
        rows[0]
        if len(rows) > 0
        else None
    )

    second_third = (
        rows[1:3]
    )

    fourth_fifth = (
        rows[3:5]
    )

    while len(
        second_third
    ) < 2:

        second_third.append(
            None
        )

    while len(
        fourth_fifth
    ) < 2:

        fourth_fifth.append(
            None
        )

    st.markdown(
        f"""
        <div class="awards-stage">

            <div class="awards-kicker">
                DIFFUSION AX CONTEST
            </div>

            <div class="awards-title">

                🏆

                <span class="goldword">
                    AWARDS
                </span>

            </div>

            <div class="awards-sub">
                혁신의 아이디어가
                더 나은 현장을 만듭니다
            </div>


            <div class="podium-wrap">

                <div class="award-col silver">

                    <div class="award-head">

                        <span class="medal">
                            🥈
                        </span>

                        <span class="award-name">
                            우수상
                            <small>
                                (2팀)
                            </small>
                        </span>

                    </div>


                    <div class="person-grid">

                        {person_card(
                            second_third[0]
                        )}

                        {person_card(
                            second_third[1]
                        )}

                    </div>


                    <div class="podium-base">

                        <span>
                            2
                        </span>

                    </div>

                </div>


                <div class="award-col gold">

                    <div class="award-head">

                        <span class="medal">
                            🥇
                        </span>

                        <span class="award-name">
                            최우수상
                            <small>
                                (1팀)
                            </small>
                        </span>

                    </div>


                    <div class="person-grid">

                        {person_card(
                            first
                        )}

                    </div>


                    <div class="podium-base">

                        <span>
                            1
                        </span>

                    </div>

                </div>


                <div class="award-col bronze">

                    <div class="award-head">

                        <span class="medal">
                            🥉
                        </span>

                        <span class="award-name">
                            장려상
                            <small>
                                (2팀)
                            </small>
                        </span>

                    </div>


                    <div class="person-grid">

                        {person_card(
                            fourth_fifth[0]
                        )}

                        {person_card(
                            fourth_fifth[1]
                        )}

                    </div>


                    <div class="podium-base">

                        <span>
                            3
                        </span>

                    </div>

                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


def render_result_table(result):

    body = []

    for _, r in result.iterrows():

        rank = int(
            r["순위"]
        )

        if rank == 1:

            badge = "r1"

            award = (
                "🥇 최우수"
            )

        elif rank in (
            2,
            3,
        ):

            badge = "r2"

            award = (
                "🥈 우수"
            )

        else:

            badge = "r3"

            award = (
                "🥉 장려"
            )

        body.append(
            f"""
            <tr>

                <td>

                    <span class="rank-badge {badge}">
                        {rank}
                    </span>

                </td>

                <td class="team-bold">
                    {esc(
                        show_value(
                            r["팀"],
                            "",
                        )
                    )}
                </td>

                <td>
                    {esc(
                        show_value(
                            r["발표자"],
                            "",
                        )
                    )}
                </td>

                <td class="title-left">
                    {esc(
                        show_value(
                            r["제목"],
                            "",
                        )
                    )}
                </td>

                <td>
                    {int(
                        r["현업문제"]
                    )}
                </td>

                <td>
                    {int(
                        r["업무효과"]
                    )}
                </td>

                <td>
                    {int(
                        r["완성도"]
                    )}
                </td>

                <td>
                    {int(
                        r["활용편의"]
                    )}
                </td>

                <td>
                    {int(
                        r["확산가능"]
                    )}
                </td>

                <td>
                    <b>
                        {int(
                            r["최종점수"]
                        )}
                    </b>
                </td>

                <td>
                    {int(
                        r["제출인원"]
                    )}/9
                </td>

                <td>
                    {award}
                </td>

            </tr>
            """
        )

    st.markdown(
        f"""
        <div class="section-card">

            <div class="section-title">

                📊 최종 결과표

                <small>
                    가중치 반영 실시간 집계
                </small>

            </div>


            <div class="table-scroll">

                <table class="ax-table">

                    <thead>

                        <tr>

                            <th>
                                순위
                            </th>

                            <th>
                                팀
                            </th>

                            <th>
                                발표자
                            </th>

                            <th>
                                제목
                            </th>

                            <th>
                                현업문제
                            </th>

                            <th>
                                업무효과
                            </th>

                            <th>
                                완성도
                            </th>

                            <th>
                                활용편의
                            </th>

                            <th>
                                확산가능
                            </th>

                            <th>
                                총점
                            </th>

                            <th>
                                제출
                            </th>

                            <th>
                                현재 수상
                            </th>

                        </tr>

                    </thead>

                    <tbody>
                        {''.join(body)}
                    </tbody>

                </table>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


def render_comments(
    comments_df,
    result,
):

    st.markdown(
        """
        <div class="section-title">

            💬 심사위원 코멘트

            <small>
                DIFF_CHAMPION →
                DIFF_STRAT →
                나머지 ABC 순
            </small>

        </div>
        """,
        unsafe_allow_html=True,
    )

    if comments_df.empty:

        st.info(
            "아직 등록된 코멘트가 없습니다."
        )

        return


    agent_map = {

        int(
            r["slot"]
        ):
        {
            "title":
                show_value(
                    r["제목"],
                    f"Agent {int(r['slot'])}",
                ),

            "team":
                show_value(
                    r["팀"],
                    "",
                ),
        }

        for _, r
        in result.iterrows()
    }


    comments_df = (
        comments_df.copy()
    )

    comments_df[
        "judge_order"
    ] = (
        comments_df[
            "judge"
        ]
        .map(
            JUDGE_ORDER
        )
        .fillna(
            999
        )
    )

    comments_df = (
        comments_df
        .sort_values(
            [
                "judge_order",
                "agent_slot",
            ]
        )
    )


    cards = []

    for _, row in comments_df.iterrows():

        slot = int(
            row["agent_slot"]
        )

        info = (
            agent_map.get(
                slot,
                {
                    "title":
                        f"Agent {slot}",

                    "team":
                        "",
                },
            )
        )

        champion = (
            " champion"
            if row["judge"]
            == "DIFF_CHAMPION"
            else ""
        )

        cards.append(
            f"""
            <div class="comment-card{champion}">

                <div class="comment-top">

                    <div class="comment-judge">
                        {esc(
                            row["judge"]
                        )}
                    </div>

                    <div class="comment-agent">

                        {esc(
                            info["team"]
                        )}

                        <br>

                        {esc(
                            info["title"]
                        )}

                    </div>

                </div>


                <div class="comment-body">

                    {esc(
                        row["comment"]
                    )}

                </div>


                <div class="comment-score">

                    원점수
                    {int(
                        row["total"]
                    )}

                    · 가중치
                    {int(
                        row["weight"]
                    )}

                    · 반영
                    {int(
                        row["weighted_total"]
                    )}

                </div>

            </div>
            """
        )


    st.markdown(
        f"""
        <div class="section-card">

            <div class="comments-grid">

                {''.join(cards)}

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# LOGIN
# ------------------------------------------------------------
if "user" not in st.session_state:

    render_brand()

    left, center, right = (
        st.columns(
            [
                1,
                1.25,
                1,
            ]
        )
    )

    with center:

        st.markdown(
            '<div class="glass-card">',
            unsafe_allow_html=True,
        )

        st.markdown(
            "### 🏆 DIFFUSION AX 경진대회"
        )

        st.caption(
            "심사위원 또는 MASTER 계정으로 로그인하세요."
        )

        with st.form(
            "login_form"
        ):

            username = (
                st.selectbox(
                    "접속자명",
                    list(
                        USERS.keys()
                    ),
                    index=None,
                    placeholder=(
                        "접속자명을 선택하세요"
                    ),
                )
            )

            password = (
                st.text_input(
                    "비밀번호",
                    type="password",
                    placeholder=(
                        "비밀번호 입력"
                    ),
                )
            )

            submitted = (
                st.form_submit_button(
                    "로그인",
                    use_container_width=True,
                )
            )

        if submitted:

            if (
                username in USERS
                and USERS[
                    username
                ][
                    "password"
                ]
                == password
            ):

                st.session_state[
                    "user"
                ] = username

                st.session_state[
                    "role"
                ] = USERS[
                    username
                ][
                    "role"
                ]

                st.rerun()

            else:

                st.error(
                    "접속자명 또는 비밀번호가 올바르지 않습니다."
                )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

    st.stop()


user = (
    st.session_state[
        "user"
    ]
)

role = (
    st.session_state[
        "role"
    ]
)


render_brand(
    user
)


c1, c2 = (
    st.columns(
        [
            8,
            1,
        ]
    )
)

with c2:

    if st.button(
        "로그아웃",
        use_container_width=True,
    ):

        logout()


# ------------------------------------------------------------
# JUDGE
# ------------------------------------------------------------
if role == "judge":

    weight = (
        USERS[
            user
        ][
            "weight"
        ]
    )

    if weight == 3:

        st.warning(
            "DIFF_CHAMPION 채점은 **3배 가중치**로 최종 집계됩니다."
        )

    else:

        st.info(
            "채점 결과는 **1배 가중치**로 최종 집계됩니다."
        )


    agents = (
        get_agents()
    )


    agent_map = {

        (
            f"{a['slot']}. "
            f"{agent_display_title(a)}"
        ):
        a["slot"]

        for a
        in agents
    }


    selected_label = (
        st.selectbox(
            "평가할 Agent",
            list(
                agent_map.keys()
            ),
        )
    )


    slot = (
        agent_map[
            selected_label
        ]
    )


    selected_agent = next(

        a

        for a
        in agents

        if int(
            a["slot"]
        )
        == int(
            slot
        )
    )


    render_agent_card(
        selected_agent
    )


    old = (
        get_score(
            user,
            slot,
        )
    )


    defaults = [
        3,
        3,
        3,
        3,
        3,
    ]

    old_comment = ""


    if old:

        defaults = [

            int(
                old[
                    f"c{i}"
                ]
            )

            for i
            in range(
                1,
                6,
            )
        ]

        old_comment = (
            old.get(
                "comment"
            )
            or ""
        )

        st.success(
            "이미 제출한 Agent입니다. 다시 제출하면 기존 점수가 수정됩니다."
        )


    st.caption(
        "1점 미흡 · 2점 다소 미흡 · 3점 보통 · 4점 우수 · 5점 매우 우수"
    )


    values = []


    with st.form(
        f"score_form_{slot}"
    ):

        for i, (
            name,
            description,
        ) in enumerate(
            CRITERIA
        ):

            st.markdown(
                f"**{i + 1}. {name}**"
            )

            st.caption(
                description
            )

            values.append(
                st.radio(
                    name,
                    [
                        1,
                        2,
                        3,
                        4,
                        5,
                    ],
                    index=(
                        defaults[i]
                        - 1
                    ),
                    horizontal=True,
                    label_visibility="collapsed",
                    key=(
                        f"{user}_"
                        f"{slot}_"
                        f"c{i+1}"
                    ),
                )
            )


        comment = (
            st.text_input(
                "한줄 의견 (선택)",
                value=(
                    old_comment
                ),
                placeholder=(
                    "Agent에 대한 의견이 있으면 입력"
                ),
            )
        )


        submit_score = (
            st.form_submit_button(
                "✅ 점수 제출 / 수정",
                use_container_width=True,
            )
        )


    st.metric(
        "입력 합계",
        f"{sum(values)} / 25점",
    )


    if submit_score:

        try:

            save_score(
                user,
                slot,
                values,
                comment,
            )

            st.success(
                f"{selected_label} 채점 완료 · {sum(values)}/25점"
            )

        except Exception as e:

            st.error(
                "저장 중 오류가 발생했습니다. 다시 제출해 주세요."
            )

            st.caption(
                str(e)
            )


    rows = (
        get_all_scores()
    )


    done_slots = {

        int(
            r[
                "agent_slot"
            ]
        )

        for r
        in rows

        if r.get(
            "judge"
        )
        == user
    }


    st.progress(
        len(
            done_slots
        )
        / 5
    )


    st.caption(
        f"내 채점 진행률: "
        f"{len(done_slots)}/5 "
        f"Agent 완료"
    )


    st.stop()


# ------------------------------------------------------------
# MASTER
# ------------------------------------------------------------
st.success(
    "MASTER 관리자 모드 · 실시간 집계"
)


tab_result, tab_status, tab_settings = (
    st.tabs(
        [
            "🏆 결과 보기",
            "✅ 제출 현황",
            "⚙️ Agent 설정",
        ]
    )
)


# ------------------------------------------------------------
# MASTER - RESULT
# ------------------------------------------------------------
with tab_result:

    @st.fragment(
        run_every="3s"
    )
    def live_results():

        result, score_df = (
            build_aggregate()
        )


        result = (
            result
            .sort_values(
                [
                    "최종점수",
                    "slot",
                ],
                ascending=[
                    False,
                    True,
                ],
            )
            .reset_index(
                drop=True
            )
        )


        result.insert(
            0,
            "순위",
            range(
                1,
                len(result) + 1,
            ),
        )


        completed_judges = 0


        if not score_df.empty:

            counts = (
                score_df
                .groupby(
                    "judge"
                )[
                    "agent_slot"
                ]
                .nunique()
            )

            completed_judges = sum(

                int(
                    counts.get(
                        j,
                        0,
                    )
                )
                == 5

                for j
                in JUDGES
            )


        m1, m2, m3 = (
            st.columns(
                3
            )
        )


        m1.metric(
            "채점 완료 심사위원",
            f"{completed_judges} / 9",
        )


        m2.metric(
            "최종점수 만점",
            f"{MAX_TOTAL}점",
        )


        m3.metric(
            "자동 갱신",
            "3초",
        )


        render_awards_stage(
            result
        )


        render_result_table(
            result
        )


        if completed_judges < 9:

            st.caption(
                "※ 아직 모든 심사위원의 채점이 완료되지 않았으므로 순위는 변동될 수 있습니다."
            )

        else:

            st.success(
                "9명 전원의 5개 Agent 채점이 완료되었습니다. 최종 결과를 확정할 수 있습니다."
            )


        comments_df = (
            pd.DataFrame()
        )


        if (
            not score_df.empty
            and "comment"
            in score_df.columns
        ):

            comments_df = (
                score_df.copy()
            )

            comments_df[
                "comment"
            ] = (
                comments_df[
                    "comment"
                ]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            comments_df = (
                comments_df[
                    comments_df[
                        "comment"
                    ]
                    != ""
                ]
                .copy()
            )


        render_comments(
            comments_df,
            result,
        )


        csv = (
            result
            .to_csv(
                index=False
            )
            .encode(
                "utf-8-sig"
            )
        )


        st.download_button(
            "⬇️ 최종 결과 CSV 다운로드",
            data=csv,
            file_name=(
                "DIFFUSION_AX_최종결과.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )


    live_results()


# ------------------------------------------------------------
# MASTER - STATUS
# ------------------------------------------------------------
with tab_status:

    @st.fragment(
        run_every="3s"
    )
    def live_status():

        agents = (
            get_agents()
        )


        score_df = (
            pd.DataFrame(
                get_all_scores()
            )
        )


        rows = []


        for judge in JUDGES:

            row = {
                "심사위원":
                    judge,

                "가중치":
                    USERS[
                        judge
                    ][
                        "weight"
                    ],
            }


            for agent in agents:

                if score_df.empty:

                    done = False

                else:

                    done = (

                        (
                            score_df[
                                "judge"
                            ]
                            == judge
                        )

                        &

                        (
                            score_df[
                                "agent_slot"
                            ]
                            .astype(int)
                            == int(
                                agent[
                                    "slot"
                                ]
                            )
                        )

                    ).any()


                label = (
                    agent_display_title(
                        agent
                    )
                )


                row[
                    label
                ] = (
                    "✅"
                    if done
                    else "—"
                )


            rows.append(
                row
            )


        st.markdown(
            "### ✅ 제출 현황"
        )


        st.caption(
            "DIFF_CHAMPION → DIFF_STRAT → 나머지 ABC 순"
        )


        st.dataframe(
            pd.DataFrame(
                rows
            ),
            use_container_width=True,
            hide_index=True,
        )


        complete_count = (

            0

            if score_df.empty

            else len(

                score_df
                .drop_duplicates(
                    subset=[
                        "judge",
                        "agent_slot",
                    ]
                )

            )
        )


        st.progress(
            min(
                complete_count
                / 45,
                1.0,
            )
        )


        st.caption(
            f"전체 채점 진행률: "
            f"{complete_count}/45"
        )


    live_status()


# ------------------------------------------------------------
# MASTER - SETTINGS
# ------------------------------------------------------------
with tab_settings:

    st.markdown(
        "### ⚙️ Agent 발표 정보 설정"
    )


    st.caption(
        "팀 / 발표자 / 제목을 입력하면 포디움·결과표·심사위원 화면에 즉시 반영됩니다."
    )


    agents = (
        get_agents()
    )


    with st.form(
        "agent_settings_form"
    ):

        edited = {}


        for agent in agents:

            slot = int(
                agent[
                    "slot"
                ]
            )


            st.markdown(
                '<div class="agent-setting">',
                unsafe_allow_html=True,
            )


            st.markdown(
                f"#### Agent {slot}"
            )


            name = (
                st.text_input(
                    f"Agent {slot} 내부명",
                    value=(
                        agent[
                            "name"
                        ]
                    ),
                    key=(
                        f"name_{slot}"
                    ),
                )
            )


            cc1, cc2 = (
                st.columns(
                    2
                )
            )


            with cc1:

                team = (
                    st.text_input(
                        f"Agent {slot} 팀",
                        value=(
                            agent[
                                "team"
                            ]
                        ),
                        placeholder=(
                            "예: DRAM_ALD"
                        ),
                        key=(
                            f"team_{slot}"
                        ),
                    )
                )


            with cc2:

                presenter = (
                    st.text_input(
                        f"Agent {slot} 발표자",
                        value=(
                            agent[
                                "presenter"
                            ]
                        ),
                        placeholder=(
                            "예: 홍길동"
                        ),
                        key=(
                            f"presenter_{slot}"
                        ),
                    )
                )


            title = (
                st.text_input(
                    f"Agent {slot} 제목",
                    value=(
                        agent[
                            "title"
                        ]
                    ),
                    placeholder=(
                        "예: DORIS Super Agent"
                    ),
                    key=(
                        f"title_{slot}"
                    ),
                )
            )


            edited[
                slot
            ] = {

                "name":
                    name,

                "team":
                    team,

                "presenter":
                    presenter,

                "title":
                    title,
            }


            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )


        save_agents = (
            st.form_submit_button(
                "💾 발표 정보 저장",
                use_container_width=True,
            )
        )


    if save_agents:

        try:

            for (
                slot,
                values,
            ) in edited.items():

                update_agent(
                    slot,
                    values[
                        "name"
                    ],
                    values[
                        "team"
                    ],
                    values[
                        "presenter"
                    ],
                    values[
                        "title"
                    ],
                )


            st.success(
                "5개 Agent 발표 정보가 저장되었습니다."
            )


            st.rerun()


        except Exception as e:

            st.error(
                "발표 정보 저장에 실패했습니다."
            )

            st.caption(
                str(e)
            )


    st.divider()


    st.markdown(
        "### 🗑 행사 전 테스트 점수 초기화"
    )


    confirm = (
        st.checkbox(
            "모든 채점 데이터 삭제에 동의합니다."
        )
    )


    if st.button(
        "전체 점수 초기화",
        disabled=(
            not confirm
        ),
        use_container_width=True,
    ):

        try:

            clear_all_scores()

            st.success(
                "모든 점수가 초기화되었습니다."
            )

            st.rerun()


        except Exception as e:

            st.error(
                "초기화에 실패했습니다."
            )

            st.caption(
                str(e)
            )
