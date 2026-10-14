import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from supabase import create_client

st.set_page_config(
    page_title="DIFFUSION AX 경진대회",
    page_icon="🏆",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ============================================================
# 기본 설정
# ============================================================

USERS = {
    "DRAM_ALD": {
        "password": "1026",
        "role": "judge",
        "weight": 1
    },
    "DRAM_FUR": {
        "password": "2026",
        "role": "judge",
        "weight": 1
    },
    "DRAM_IMP": {
        "password": "3026",
        "role": "judge",
        "weight": 1
    },
    "NAND_ALD": {
        "password": "4026",
        "role": "judge",
        "weight": 1
    },
    "NAND_FUR": {
        "password": "5026",
        "role": "judge",
        "weight": 1
    },
    "NAND_IMP": {
        "password": "6026",
        "role": "judge",
        "weight": 1
    },
    "M15X_DIFF": {
        "password": "7026",
        "role": "judge",
        "weight": 1
    },
    "DIFF_STRAT": {
        "password": "8026",
        "role": "judge",
        "weight": 1
    },
    "DIFF_CHAMPION": {
        "password": "9026",
        "role": "judge",
        "weight": 3
    },

    "MASTER": {
        "password": "2006",
        "role": "admin",
        "weight": 0
    },
}


CRITERIA = [
    (
        "현업 문제 해결성",
        "실제 현장의 Pain Point / Needs를 제대로 해결하는가?"
    ),
    (
        "업무 효과",
        "시간 단축·품질 향상·Risk 감소 등 효과가 명확한가?"
    ),
    (
        "Agent 완성도",
        "정확성·신뢰성이 실제 업무 활용 가능한 수준인가?"
    ),
    (
        "활용 편의성",
        "쉽게 사용 가능하며 Legacy System/데이터 조회와 잘 연결되는가?"
    ),
    (
        "확산 가능성",
        "다른 공정·팀에도 Skill/Tool/Agent 형태로 재사용·확산 가능한가?"
    ),
]


JUDGES = [
    u for u, cfg in USERS.items()
    if cfg["role"] == "judge"
]

MAX_WEIGHT_SUM = sum(
    USERS[u]["weight"]
    for u in JUDGES
)

MAX_TOTAL = 25 * MAX_WEIGHT_SUM


# ============================================================
# SUPABASE 연결
# ============================================================

@st.cache_resource
def get_db():

    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    return create_client(url, key)


db = get_db()


# ============================================================
# DB 함수
# ============================================================

def get_agents():

    rows = (
        db.table("agents")
        .select("slot,name")
        .order("slot")
        .execute()
        .data
        or []
    )

    if len(rows) < 5:

        return [
            {
                "slot": i,
                "name": f"Agent {i}"
            }
            for i in range(1, 6)
        ]

    return rows


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
    vals,
    comment
):

    weight = USERS[judge]["weight"]

    total = sum(vals)

    payload = {

        "judge": judge,

        "agent_slot": slot,

        "c1": vals[0],
        "c2": vals[1],
        "c3": vals[2],
        "c4": vals[3],
        "c5": vals[4],

        "total": total,

        "weight": weight,

        "weighted_total":
            total * weight,

        "comment":
            comment.strip(),

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }

    (
        db.table("scores")
        .upsert(
            payload,
            on_conflict="judge,agent_slot"
        )
        .execute()
    )


def update_agent_name(
    slot,
    name
):

    name = (
        name.strip()
        or f"Agent {slot}"
    )

    (
        db.table("agents")
        .upsert(
            {
                "slot": slot,
                "name": name
            },
            on_conflict="slot"
        )
        .execute()
    )


def clear_all_scores():

    (
        db.table("scores")
        .delete()
        .neq(
            "judge",
            "__never__"
        )
        .execute()
    )


def logout():

    st.session_state.pop(
        "user",
        None
    )

    st.session_state.pop(
        "role",
        None
    )

    st.rerun()


# ============================================================
# 화면 스타일
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 900px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }

    div[data-testid="stRadio"] > div {
        gap: .35rem;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.65rem;
    }

    .stButton button {
        min-height: 46px;
        border-radius: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 로그인
# ============================================================

if "user" not in st.session_state:

    st.markdown(
        "## 🏆 DIFFUSION AX 경진대회"
    )

    st.caption(
        "모바일 실시간 채점 시스템"
    )

    with st.form(
        "login_form"
    ):

        username = st.selectbox(

            "접속자명",

            list(
                USERS.keys()
            ),

            index=None,

            placeholder=
            "접속자명을 선택하세요"
        )

        password = st.text_input(

            "비밀번호",

            type="password",

            placeholder=
            "비밀번호 입력"
        )

        submitted = (
            st.form_submit_button(
                "로그인",
                use_container_width=True
            )
        )

    if submitted:

        if (
            username in USERS
            and
            USERS[username]["password"]
            == password
        ):

            st.session_state[
                "user"
            ] = username

            st.session_state[
                "role"
            ] = USERS[
                username
            ]["role"]

            st.rerun()

        else:

            st.error(
                "접속자명 또는 비밀번호가 올바르지 않습니다."
            )

    st.stop()


user = st.session_state[
    "user"
]

role = st.session_state[
    "role"
]


# ============================================================
# 상단
# ============================================================

a, b = st.columns(
    [4, 1.2]
)

with a:

    st.markdown(
        "### 🏆 DIFFUSION AX 경진대회"
    )

    st.caption(
        f"접속자: {user}"
    )


with b:

    if st.button(
        "로그아웃",
        use_container_width=True
    ):

        logout()


# ============================================================
# 심사위원 화면
# ============================================================

if role == "judge":

    weight = USERS[
        user
    ]["weight"]

    if weight == 3:

        st.warning(
            "DIFF_CHAMPION 채점은 "
            "**3배 가중치**로 "
            "최종 집계됩니다."
        )

    else:

        st.info(
            "채점 결과는 "
            "**1배 가중치**로 "
            "최종 집계됩니다."
        )


    agents = get_agents()

    agent_map = {

        f"{r['slot']}. {r['name']}":
        r["slot"]

        for r in agents
    }


    selected_label = (
        st.selectbox(
            "평가할 Agent",
            list(
                agent_map.keys()
            )
        )
    )

    slot = agent_map[
        selected_label
    ]


    old = get_score(
        user,
        slot
    )


    defaults = [
        3,
        3,
        3,
        3,
        3
    ]

    old_comment = ""


    if old:

        defaults = [

            int(
                old[
                    f"c{i}"
                ]
            )

            for i in range(
                1,
                6
            )
        ]

        old_comment = (
            old.get(
                "comment"
            )
            or ""
        )

        st.success(
            "이미 제출한 Agent입니다. "
            "다시 제출하면 기존 점수가 수정됩니다."
        )


    st.caption(
        "1점 미흡 · "
        "2점 다소 미흡 · "
        "3점 보통 · "
        "4점 우수 · "
        "5점 매우 우수"
    )


    vals = []


    with st.form(
        f"score_form_{slot}"
    ):

        for i, (
            name,
            desc
        ) in enumerate(
            CRITERIA
        ):

            st.markdown(
                f"**{i+1}. {name}**"
            )

            st.caption(
                desc
            )

            val = st.radio(

                name,

                [
                    1,
                    2,
                    3,
                    4,
                    5
                ],

                index=
                defaults[i] - 1,

                horizontal=True,

                label_visibility=
                "collapsed",

                key=
                f"{user}_{slot}_c{i+1}"
            )

            vals.append(
                val
            )


        comment = st.text_input(

            "한줄 의견 (선택)",

            value=
            old_comment,

            placeholder=
            "Agent에 대한 의견이 있으면 입력"
        )


        submit_score = (
            st.form_submit_button(

                "✅ 점수 제출 / 수정",

                use_container_width=True
            )
        )


    st.metric(

        "입력 합계",

        f"{sum(vals)} / 25점"
    )


    if submit_score:

        try:

            save_score(
                user,
                slot,
                vals,
                comment
            )

            st.success(
                f"{selected_label} "
                f"채점 완료 · "
                f"{sum(vals)}/25점"
            )

        except Exception as e:

            st.error(
                "저장 중 오류가 발생했습니다. "
                "네트워크 연결 후 "
                "다시 제출해 주세요."
            )

            st.caption(
                str(e)
            )


    all_rows = (
        get_all_scores()
    )


    done_slots = {

        int(
            r["agent_slot"]
        )

        for r in all_rows

        if r.get(
            "judge"
        ) == user
    }


    st.progress(
        len(done_slots) / 5
    )

    st.caption(
        f"내 채점 진행률: "
        f"{len(done_slots)}/5 "
        f"Agent 완료"
    )

    st.stop()


# ============================================================
# MASTER 관리자
# ============================================================

st.success(
    "MASTER 관리자 모드 · 실시간 집계"
)


tab_result, tab_status, tab_settings = (
    st.tabs(
        [
            "📊 실시간 결과",
            "✅ 제출 현황",
            "⚙️ Agent 설정"
        ]
    )
)


# ============================================================
# 집계 함수
# ============================================================

def build_aggregate():

    agents = get_agents()

    score_rows = (
        get_all_scores()
    )

    score_df = (
        pd.DataFrame(
            score_rows
        )
    )


    base = pd.DataFrame({

        "slot":
        [
            a["slot"]
            for a in agents
        ],

        "Agent":
        [
            a["name"]
            for a in agents
        ]
    })


    if score_df.empty:

        for col in [

            "현업문제",
            "업무효과",
            "완성도",
            "활용편의",
            "확산가능",
            "최종점수",
            "제출인원"

        ]:

            base[col] = 0

        return (
            base,
            score_df
        )


    for i in range(
        1,
        6
    ):

        score_df[
            f"wc{i}"
        ] = (

            score_df[
                f"c{i}"
            ]

            *

            score_df[
                "weight"
            ]
        )


    agg = (
        score_df
        .groupby(
            "agent_slot",
            as_index=False
        )
        .agg(

            현업문제=(
                "wc1",
                "sum"
            ),

            업무효과=(
                "wc2",
                "sum"
            ),

            완성도=(
                "wc3",
                "sum"
            ),

            활용편의=(
                "wc4",
                "sum"
            ),

            확산가능=(
                "wc5",
                "sum"
            ),

            최종점수=(
                "weighted_total",
                "sum"
            ),

            제출인원=(
                "judge",
                "nunique"
            )
        )
    )


    out = base.merge(

        agg,

        left_on="slot",

        right_on=
        "agent_slot",

        how="left"
    )


    out = (
        out
        .drop(
            columns=[
                "agent_slot"
            ],
            errors="ignore"
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
        "제출인원"
    ]


    out[
        numeric
    ] = out[
        numeric
    ].astype(int)


    return (
        out,
        score_df
    )


# ============================================================
# MASTER - 실시간 결과
# ============================================================

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
                    "slot"
                ],

                ascending=[
                    False,
                    True
                ]
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
                len(result) + 1
            )
        )


        awards = []


        for i in range(
            len(result)
        ):

            if i == 0:

                awards.append(
                    "🥇 최우수"
                )

            elif i in (
                1,
                2
            ):

                awards.append(
                    "🥈 우수"
                )

            else:

                awards.append(
                    "🏅 장려"
                )


        result[
            "현재 수상"
        ] = awards


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
                        0
                    )
                ) == 5

                for j in JUDGES
            )


        c1, c2, c3 = (
            st.columns(3)
        )


        c1.metric(

            "채점 완료 심사위원",

            f"{completed_judges} / 9"
        )


        c2.metric(

            "최종점수 만점",

            f"{MAX_TOTAL}점"
        )


        c3.metric(

            "자동 갱신",

            "3초"
        )


        st.markdown(
            "#### 🏆 종합 점수"
        )


        st.dataframe(

            result[
                [
                    "순위",
                    "Agent",
                    "현업문제",
                    "업무효과",
                    "완성도",
                    "활용편의",
                    "확산가능",
                    "최종점수",
                    "제출인원",
                    "현재 수상"
                ]
            ],

            use_container_width=True,

            hide_index=True
        )


        if completed_judges < 9:

            st.caption(
                "※ 아직 모든 심사위원의 "
                "채점이 완료되지 않았으므로 "
                "순위는 변동될 수 있습니다."
            )

        else:

            st.success(
                "9명 전원의 5개 Agent "
                "채점이 완료되었습니다. "
                "최종 결과를 확정할 수 있습니다."
            )


        # ====================================================
        # 심사위원 코멘트
        # ====================================================

        st.divider()

        st.markdown(
            "#### 💬 심사위원 코멘트"
        )

        st.caption(
            "각 심사위원이 채점 시 "
            "선택적으로 입력한 의견입니다."
        )


        agents = get_agents()


        agent_name_map = {

            int(a["slot"]):
            a["name"]

            for a in agents
        }


        if (
            score_df.empty
            or
            "comment"
            not in score_df.columns
        ):

            st.info(
                "아직 등록된 코멘트가 없습니다."
            )

        else:

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
                    ] != ""
                ]
            )


            if comments_df.empty:

                st.info(
                    "아직 등록된 코멘트가 없습니다."
                )

            else:

                comments_df[
                    "Agent"
                ] = (

                    comments_df[
                        "agent_slot"
                    ]

                    .astype(int)

                    .map(
                        agent_name_map
                    )
                )


                comments_df[
                    "심사위원"
                ] = (
                    comments_df[
                        "judge"
                    ]
                )


                comments_df[
                    "원점수"
                ] = (

                    comments_df[
                        "total"
                    ]

                    .astype(int)
                )


                comments_df[
                    "가중치"
                ] = (

                    comments_df[
                        "weight"
                    ]

                    .astype(int)
                )


                comments_df[
                    "반영점수"
                ] = (

                    comments_df[
                        "weighted_total"
                    ]

                    .astype(int)
                )


                comments_df[
                    "코멘트"
                ] = (

                    comments_df[
                        "comment"
                    ]
                )


                ranked_agents = (

                    result[
                        "Agent"
                    ]

                    .tolist()
                )


                for agent_name in (
                    ranked_agents
                ):


                    agent_comments = (

                        comments_df[
                            comments_df[
                                "Agent"
                            ]
                            ==
                            agent_name
                        ]
                    )


                    if (
                        agent_comments.empty
                    ):

                        continue


                    with st.expander(

                        f"💬 "
                        f"{agent_name} "
                        f"· 코멘트 "
                        f"{len(agent_comments)}건"
                    ):
