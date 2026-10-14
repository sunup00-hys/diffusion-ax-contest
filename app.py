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

# =========================================================
# 사용자 / 비밀번호
# =========================================================
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

CRITERIA = [
    ("현업 문제 해결성", "실제 현장의 Pain Point / Needs를 제대로 해결하는가?"),
    ("업무 효과", "시간 단축·품질 향상·Risk 감소 등 효과가 명확한가?"),
    ("Agent 완성도", "정확성·신뢰성이 실제 업무 활용 가능한 수준인가?"),
    ("활용 편의성", "쉽게 사용 가능하며 Legacy System/데이터 조회와 잘 연결되는가?"),
    ("확산 가능성", "다른 공정·팀에도 Skill/Tool/Agent 형태로 재사용·확산 가능한가?"),
]

JUDGES = [
    user
    for user, config in USERS.items()
    if config["role"] == "judge"
]

MAX_TOTAL = 25 * sum(USERS[user]["weight"] for user in JUDGES)


# =========================================================
# Supabase
# =========================================================
@st.cache_resource
def get_db():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


db = get_db()


# =========================================================
# DB 함수
# =========================================================
def get_agents():
    rows = (
        db.table("agents")
        .select("slot,name")
        .order("slot")
        .execute()
        .data
        or []
    )

    if len(rows) >= 5:
        return rows

    return [
        {"slot": i, "name": f"Agent {i}"}
        for i in range(1, 6)
    ]


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


def save_score(judge, slot, values, comment):
    weight = USERS[judge]["weight"]
    total = sum(values)

    payload = {
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
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    (
        db.table("scores")
        .upsert(
            payload,
            on_conflict="judge,agent_slot"
        )
        .execute()
    )


def update_agent_name(slot, name):
    name = name.strip() or f"Agent {slot}"

    (
        db.table("agents")
        .upsert(
            {
                "slot": slot,
                "name": name,
            },
            on_conflict="slot"
        )
        .execute()
    )


def clear_all_scores():
    (
        db.table("scores")
        .delete()
        .neq("judge", "__never__")
        .execute()
    )


def logout():
    st.session_state.clear()
    st.rerun()


# =========================================================
# 스타일
# =========================================================
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

    .stButton button {
        min-height: 46px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 로그인
# =========================================================
if "user" not in st.session_state:
    st.markdown("## 🏆 DIFFUSION AX 경진대회")
    st.caption("모바일 실시간 채점 시스템")

    with st.form("login_form"):
        username = st.selectbox(
            "접속자명",
            list(USERS.keys()),
            index=None,
            placeholder="접속자명을 선택하세요",
        )

        password = st.text_input(
            "비밀번호",
            type="password",
            placeholder="비밀번호 입력",
        )

        submitted = st.form_submit_button(
            "로그인",
            use_container_width=True,
        )

    if submitted:
        if (
            username in USERS
            and USERS[username]["password"] == password
        ):
            st.session_state["user"] = username
            st.session_state["role"] = USERS[username]["role"]
            st.rerun()
        else:
            st.error("접속자명 또는 비밀번호가 올바르지 않습니다.")

    st.stop()


user = st.session_state["user"]
role = st.session_state["role"]


# =========================================================
# 상단
# =========================================================
top1, top2 = st.columns([4, 1.2])

with top1:
    st.markdown("### 🏆 DIFFUSION AX 경진대회")
    st.caption(f"접속자: {user}")

with top2:
    if st.button(
        "로그아웃",
        use_container_width=True,
    ):
        logout()


# =========================================================
# 심사위원 화면
# =========================================================
if role == "judge":
    weight = USERS[user]["weight"]

    if weight == 3:
        st.warning(
            "DIFF_CHAMPION 채점은 "
            "**3배 가중치**로 최종 집계됩니다."
        )
    else:
        st.info(
            "채점 결과는 "
            "**1배 가중치**로 최종 집계됩니다."
        )

    agents = get_agents()

    agent_map = {
        f"{item['slot']}. {item['name']}": item["slot"]
        for item in agents
    }

    selected_label = st.selectbox(
        "평가할 Agent",
        list(agent_map.keys()),
    )

    slot = agent_map[selected_label]

    old = get_score(user, slot)

    defaults = [3, 3, 3, 3, 3]
    old_comment = ""

    if old:
        defaults = [
            int(old[f"c{i}"])
            for i in range(1, 6)
        ]

        old_comment = old.get("comment") or ""

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

    values = []

    with st.form(f"score_form_{slot}"):

        for i, (name, description) in enumerate(CRITERIA):
            st.markdown(f"**{i + 1}. {name}**")
            st.caption(description)

            score = st.radio(
                name,
                [1, 2, 3, 4, 5],
                index=defaults[i] - 1,
                horizontal=True,
                label_visibility="collapsed",
                key=f"{user}_{slot}_c{i + 1}",
            )

            values.append(score)

        comment = st.text_input(
            "한줄 의견 (선택)",
            value=old_comment,
            placeholder="Agent에 대한 의견이 있으면 입력",
        )

        submit_score = st.form_submit_button(
            "✅ 점수 제출 / 수정",
            use_container_width=True,
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
                f"{selected_label} "
                f"채점 완료 · "
                f"{sum(values)}/25점"
            )

        except Exception as e:
            st.error(
                "저장 중 오류가 발생했습니다. "
                "다시 제출해 주세요."
            )
            st.caption(str(e))

    all_rows = get_all_scores()

    done_slots = {
        int(row["agent_slot"])
        for row in all_rows
        if row.get("judge") == user
    }

    st.progress(len(done_slots) / 5)

    st.caption(
        f"내 채점 진행률: "
        f"{len(done_slots)}/5 Agent 완료"
    )

    st.stop()


# =========================================================
# MASTER
# =========================================================
st.success("MASTER 관리자 모드 · 실시간 집계")

tab_result, tab_status, tab_settings = st.tabs(
    [
        "📊 실시간 결과",
        "✅ 제출 현황",
        "⚙️ Agent 설정",
    ]
)


# =========================================================
# 집계 함수
# =========================================================
def build_aggregate():
    agents = get_agents()
    score_rows = get_all_scores()
    score_df = pd.DataFrame(score_rows)

    base = pd.DataFrame(
        {
            "slot": [
                item["slot"]
                for item in agents
            ],
            "Agent": [
                item["name"]
                for item in agents
            ],
        }
    )

    if score_df.empty:
        for column in [
            "현업문제",
            "업무효과",
            "완성도",
            "활용편의",
            "확산가능",
            "최종점수",
            "제출인원",
        ]:
            base[column] = 0

        return base, score_df

    for i in range(1, 6):
        score_df[f"wc{i}"] = (
            score_df[f"c{i}"]
            * score_df["weight"]
        )

    aggregate = (
        score_df
        .groupby(
            "agent_slot",
            as_index=False,
        )
        .agg(
            현업문제=("wc1", "sum"),
            업무효과=("wc2", "sum"),
            완성도=("wc3", "sum"),
            활용편의=("wc4", "sum"),
            확산가능=("wc5", "sum"),
            최종점수=("weighted_total", "sum"),
            제출인원=("judge", "nunique"),
        )
    )

    result = base.merge(
        aggregate,
        left_on="slot",
        right_on="agent_slot",
        how="left",
    )

    result = (
        result
        .drop(
            columns=["agent_slot"],
            errors="ignore",
        )
        .fillna(0)
    )

    numeric_columns = [
        "현업문제",
        "업무효과",
        "완성도",
        "활용편의",
        "확산가능",
        "최종점수",
        "제출인원",
    ]

    result[numeric_columns] = (
        result[numeric_columns]
        .astype(int)
    )

    return result, score_df


# =========================================================
# MASTER - 실시간 결과
# =========================================================
with tab_result:

    @st.fragment(run_every="3s")
    def live_results():

        result, score_df = build_aggregate()

        result = (
            result
            .sort_values(
                ["최종점수", "slot"],
                ascending=[False, True],
            )
            .reset_index(drop=True)
        )

        result.insert(
            0,
            "순위",
            range(1, len(result) + 1),
        )

        result["현재 수상"] = [
            "🥇 최우수"
            if i == 0
            else "🥈 우수"
            if i in (1, 2)
            else "🏅 장려"
            for i in range(len(result))
        ]

        completed_judges = 0

        if not score_df.empty:
            counts = (
                score_df
                .groupby("judge")["agent_slot"]
                .nunique()
            )

            completed_judges = sum(
                int(counts.get(judge, 0)) == 5
                for judge in JUDGES
            )

        metric1, metric2, metric3 = st.columns(3)

        metric1.metric(
            "채점 완료 심사위원",
            f"{completed_judges} / 9",
        )

        metric2.metric(
            "최종점수 만점",
            f"{MAX_TOTAL}점",
        )

        metric3.metric(
            "자동 갱신",
            "3초",
        )

        st.markdown("#### 🏆 종합 점수")

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
                    "현재 수상",
                ]
            ],
            use_container_width=True,
            hide_index=True,
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

        # =================================================
        # 코멘트
        # =================================================
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
            int(item["slot"]): item["name"]
            for item in agents
        }

        if (
            score_df.empty
            or "comment" not in score_df.columns
        ):
            st.info(
                "아직 등록된 코멘트가 없습니다."
            )

        else:
            comments_df = score_df.copy()

            comments_df["comment"] = (
                comments_df["comment"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            comments_df = comments_df[
                comments_df["comment"] != ""
            ]

            if comments_df.empty:
                st.info(
                    "아직 등록된 코멘트가 없습니다."
                )

            else:
                comments_df["Agent"] = (
                    comments_df["agent_slot"]
                    .astype(int)
                    .map(agent_name_map)
                )

                comments_df["심사위원"] = (
                    comments_df["judge"]
                )

                comments_df["원점수"] = (
                    comments_df["total"]
                    .astype(int)
                )

                comments_df["가중치"] = (
                    comments_df["weight"]
                    .astype(int)
                )

                comments_df["반영점수"] = (
                    comments_df["weighted_total"]
                    .astype(int)
                )

                comments_df["코멘트"] = (
                    comments_df["comment"]
                )

                for agent_name in result["Agent"].tolist():

                    agent_comments = comments_df[
                        comments_df["Agent"]
                        == agent_name
                    ]

                    if agent_comments.empty:
                        continue

                    with st.expander(
                        f"💬 {agent_name} "
                        f"· 코멘트 "
                        f"{len(agent_comments)}건"
                    ):

                        st.dataframe(
                            agent_comments[
                                [
                                    "심사위원",
                                    "원점수",
                                    "가중치",
                                    "반영점수",
                                    "코멘트",
                                ]
                            ],
                            use_container_width=True,
                            hide_index=True,
                        )

        st.divider()

        csv = (
            result
            .to_csv(index=False)
            .encode("utf-8-sig")
        )

        st.download_button(
            "⬇️ 최종 결과 CSV 다운로드",
            data=csv,
            file_name="DIFFUSION_AX_최종결과.csv",
            mime="text/csv",
            use_container_width=True,
        )

    live_results()


# =========================================================
# MASTER - 제출 현황
# =========================================================
with tab_status:

    @st.fragment(run_every="3s")
    def live_status():

        agents = get_agents()
        rows = get_all_scores()
        score_df = pd.DataFrame(rows)

        status_rows = []

        for judge in JUDGES:

            row = {
                "심사위원": judge,
                "가중치": USERS[judge]["weight"],
            }

            for agent in agents:

                if score_df.empty:
                    done = False

                else:
                    done = (
                        (
                            score_df["judge"]
                            == judge
                        )
                        &
                        (
                            score_df["agent_slot"]
                            .astype(int)
                            == int(agent["slot"])
                        )
                    ).any()

                row[agent["name"]] = (
                    "✅"
                    if done
                    else "—"
                )

            status_rows.append(row)

        status_df = pd.DataFrame(
            status_rows
        )

        st.dataframe(
            status_df,
            use_container_width=True,
            hide_index=True,
        )

        complete_count = 0

        if not score_df.empty:
            complete_count = len(
                score_df.drop_duplicates(
                    subset=[
                        "judge",
                        "agent_slot",
                    ]
                )
            )

        st.progress(
            min(
                complete_count / 45,
                1.0,
            )
        )

        st.caption(
            f"전체 채점 진행률: "
            f"{complete_count}/45"
        )

    live_status()


# =========================================================
# MASTER - Agent 설정
# =========================================================
with tab_settings:

    st.markdown(
        "#### Agent 5개 이름 설정"
    )

    st.caption(
        "MASTER가 변경하면 "
        "모든 심사위원 휴대폰에 "
        "동일하게 반영됩니다."
    )

    agents = get_agents()

    with st.form(
        "agent_names_form"
    ):

        edited = {}

        for agent in agents:

            edited[agent["slot"]] = (
                st.text_input(
                    f"Agent {agent['slot']}",
                    value=agent["name"],
                    key=f"name_{agent['slot']}",
                )
            )

        save_names = (
            st.form_submit_button(
                "Agent명 저장",
                use_container_width=True,
            )
        )

    if save_names:

        try:
            for slot, name in edited.items():
                update_agent_name(
                    slot,
                    name,
                )

            st.success(
                "Agent명이 저장되었습니다."
            )

            st.rerun()

        except Exception as e:
            st.error(
                "Agent명 저장에 실패했습니다."
            )
            st.caption(str(e))

    st.divider()

    st.markdown(
        "#### 행사 전 테스트 점수 초기화"
    )

    confirm = st.checkbox(
        "모든 채점 데이터 삭제에 동의합니다."
    )

    if st.button(
        "🗑️ 전체 점수 초기화",
        disabled=not confirm,
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
            st.caption(str(e))
