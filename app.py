
import html
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

JUDGES = [u for u, cfg in USERS.items() if cfg["role"] == "judge"]
MAX_TOTAL = 25 * sum(USERS[u]["weight"] for u in JUDGES)


@st.cache_resource
def get_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


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
    if len(rows) >= 5:
        for row in rows:
            row["name"] = row.get("name") or f"Agent {row['slot']}"
            row["team"] = row.get("team") or ""
            row["presenter"] = row.get("presenter") or ""
            row["title"] = row.get("title") or row["name"]
        return rows

    return [
        {
            "slot": i,
            "name": f"Agent {i}",
            "team": "",
            "presenter": "",
            "title": f"Agent {i}",
        }
        for i in range(1, 6)
    ]


def get_all_scores():
    return db.table("scores").select("*").execute().data or []


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
    db.table("scores").upsert(payload, on_conflict="judge,agent_slot").execute()


def update_agent(slot, name, team, presenter, title):
    payload = {
        "slot": slot,
        "name": (name or "").strip() or f"Agent {slot}",
        "team": (team or "").strip(),
        "presenter": (presenter or "").strip(),
        "title": (title or "").strip() or f"Agent {slot}",
    }
    db.table("agents").upsert(payload, on_conflict="slot").execute()


def clear_all_scores():
    db.table("scores").delete().neq("judge", "__never__").execute()


def logout():
    st.session_state.clear()
    st.rerun()


def esc(value):
    return html.escape(str(value or ""))


def render_header(user=None):
    st.markdown('<div class="ax-title">🏆 DIFFUSION AX 경진대회</div>', unsafe_allow_html=True)
    if user:
        st.markdown(
            f'<div class="ax-subtitle">접속자: {esc(user)}</div>',
            unsafe_allow_html=True,
        )


def render_agent_info(agent):
    team = agent.get("team") or "미입력"
    presenter = agent.get("presenter") or "미입력"
    title = agent.get("title") or agent.get("name") or f"Agent {agent['slot']}"
    st.markdown(
        f"""
        <div class="agent-info">
            <div class="agent-info-title">{esc(title)}</div>
            <div class="agent-info-meta">
                <span><b>팀</b> {esc(team)}</span>
                <span><b>발표자</b> {esc(presenter)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_comment_row(agent_title, judge, total, weight, weighted_total, comment):
    st.markdown(
        f"""
        <div class="comment-row">
            <div class="comment-meta">
                <span class="comment-agent">{esc(agent_title)}</span>
                <span class="comment-judge">{esc(judge)}</span>
                <span class="comment-score">원점수 {int(total)} · 가중치 {int(weight)} · 반영 {int(weighted_total)}</span>
            </div>
            <div class="comment-text">{esc(comment)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def podium_person(row):
    team = esc(row.get("팀") or "팀 미입력")
    presenter = esc(row.get("발표자") or "발표자 미입력")
    title = esc(row.get("제목") or "")
    return f"""
        <div class="award-person">
            <div class="award-team">{team}</div>
            <div class="award-presenter">{presenter}</div>
            <div class="award-title">{title}</div>
        </div>
    """


def render_podium(result):
    if result.empty:
        return

    rows = result.to_dict("records")
    best = rows[0] if len(rows) >= 1 else None
    excellence = rows[1:3]
    encouragement = rows[3:5]

    best_html = podium_person(best) if best else '<div class="award-empty">-</div>'
    excellence_html = "".join(podium_person(r) for r in excellence) or '<div class="award-empty">-</div>'
    encouragement_html = "".join(podium_person(r) for r in encouragement) or '<div class="award-empty">-</div>'

    st.markdown(
        f"""
        <div class="award-wrap">
            <div class="award-heading">🏆 포상 결과</div>
            <div class="podium-grid">

                <div class="podium podium-silver">
                    <div class="podium-medal">🥈</div>
                    <div class="podium-label">우수</div>
                    {excellence_html}
                    <div class="podium-base podium-base-silver">2</div>
                </div>

                <div class="podium podium-gold">
                    <div class="podium-medal">🏆</div>
                    <div class="podium-label">최우수</div>
                    {best_html}
                    <div class="podium-base podium-base-gold">1</div>
                </div>

                <div class="podium podium-bronze">
                    <div class="podium-medal">🏅</div>
                    <div class="podium-label">장려</div>
                    {encouragement_html}
                    <div class="podium-base podium-base-bronze">3</div>
                </div>

            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
    .block-container {
        max-width: 940px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }

    .ax-title {
        font-size: clamp(1.55rem, 5vw, 2.15rem);
        font-weight: 800;
        line-height: 1.28;
        word-break: keep-all;
        overflow-wrap: anywhere;
        margin: 0 0 .35rem 0;
    }

    .ax-subtitle {
        font-size: 1rem;
        color: #9ca3af;
        margin-bottom: .8rem;
    }

    div[data-testid="stRadio"] > div { gap: .35rem; }

    .stButton button {
        min-height: 46px;
        border-radius: 12px;
    }

    .agent-info {
        border: 1px solid rgba(128,128,128,.28);
        border-radius: 15px;
        padding: 14px 16px;
        margin: 8px 0 16px 0;
        background: rgba(128,128,128,.06);
    }

    .agent-info-title {
        font-size: 1.1rem;
        font-weight: 800;
        line-height: 1.45;
        word-break: keep-all;
    }

    .agent-info-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 18px;
        margin-top: 8px;
        color: #aab2bf;
        font-size: .93rem;
    }

    .comment-row {
        border: 1px solid rgba(128,128,128,.28);
        border-radius: 14px;
        padding: 14px 15px;
        margin: 9px 0;
        background: rgba(128,128,128,.06);
    }

    .comment-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 7px 10px;
        align-items: center;
        margin-bottom: 8px;
    }

    .comment-agent { font-weight: 800; }
    .comment-judge { font-weight: 700; color: #cbd5e1; }
    .comment-score { font-size: .82rem; color: #9ca3af; }

    .comment-text {
        font-size: 1rem;
        line-height: 1.55;
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: keep-all;
    }

    .award-wrap {
        margin: 28px 0 20px 0;
        padding: 20px 14px 10px 14px;
        border: 1px solid rgba(128,128,128,.24);
        border-radius: 20px;
        background: linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.015));
    }

    .award-heading {
        text-align: center;
        font-size: 1.35rem;
        font-weight: 900;
        margin-bottom: 18px;
    }

    .podium-grid {
        display: grid;
        grid-template-columns: 1fr 1.12fr 1fr;
        gap: 10px;
        align-items: end;
    }

    .podium {
        text-align: center;
        border-radius: 16px 16px 8px 8px;
        padding: 12px 8px 0 8px;
        border: 1px solid rgba(255,255,255,.12);
        min-width: 0;
    }

    .podium-silver {
        background: linear-gradient(180deg, rgba(192,192,192,.16), rgba(192,192,192,.045));
    }

    .podium-gold {
        background: linear-gradient(180deg, rgba(255,205,65,.22), rgba(255,205,65,.06));
        padding-top: 18px;
    }

    .podium-bronze {
        background: linear-gradient(180deg, rgba(205,127,50,.18), rgba(205,127,50,.05));
    }

    .podium-medal {
        font-size: 1.65rem;
        line-height: 1;
    }

    .podium-label {
        font-size: 1.05rem;
        font-weight: 900;
        margin: 6px 0 10px 0;
    }

    .award-person {
        padding: 8px 3px;
        border-top: 1px solid rgba(255,255,255,.08);
    }

    .award-person:first-of-type {
        border-top: none;
    }

    .award-team {
        font-size: .95rem;
        font-weight: 800;
        line-height: 1.35;
        word-break: keep-all;
    }

    .award-presenter {
        font-size: .86rem;
        font-weight: 700;
        color: #d1d5db;
        margin-top: 2px;
    }

    .award-title {
        font-size: .72rem;
        color: #9ca3af;
        line-height: 1.35;
        margin-top: 4px;
        word-break: keep-all;
    }

    .podium-base {
        margin: 10px -8px 0 -8px;
        padding: 10px 4px;
        font-weight: 900;
        font-size: 1.25rem;
        border-radius: 0 0 8px 8px;
    }

    .podium-base-gold {
        padding: 16px 4px;
        background: rgba(255,205,65,.25);
    }

    .podium-base-silver {
        padding: 10px 4px;
        background: rgba(192,192,192,.19);
    }

    .podium-base-bronze {
        padding: 7px 4px;
        background: rgba(205,127,50,.20);
    }

    @media (max-width: 520px) {
        .block-container {
            padding-top: .9rem;
            padding-left: .9rem;
            padding-right: .9rem;
        }

        .ax-title {
            font-size: 1.55rem;
        }

        .podium-grid {
            gap: 6px;
        }

        .podium {
            padding-left: 5px;
            padding-right: 5px;
        }

        .award-team { font-size: .83rem; }
        .award-presenter { font-size: .78rem; }
        .award-title { font-size: .66rem; }
        .podium-label { font-size: .92rem; }
        .podium-medal { font-size: 1.4rem; }

        .podium-base {
            margin-left: -5px;
            margin-right: -5px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# 로그인
if "user" not in st.session_state:
    render_header()
    st.caption("모바일 실시간 채점 시스템")

    with st.form("login_form"):
        username = st.selectbox(
            "접속자명",
            list(USERS.keys()),
            index=None,
            placeholder="접속자명을 선택하세요",
        )
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력")
        submitted = st.form_submit_button("로그인", use_container_width=True)

    if submitted:
        if username in USERS and USERS[username]["password"] == password:
            st.session_state["user"] = username
            st.session_state["role"] = USERS[username]["role"]
            st.rerun()
        else:
            st.error("접속자명 또는 비밀번호가 올바르지 않습니다.")
    st.stop()


user = st.session_state["user"]
role = st.session_state["role"]

render_header(user)

if st.button("로그아웃", use_container_width=True):
    logout()


# 심사위원 화면
if role == "judge":
    weight = USERS[user]["weight"]

    if weight == 3:
        st.warning("DIFF_CHAMPION 채점은 **3배 가중치**로 최종 집계됩니다.")
    else:
        st.info("채점 결과는 **1배 가중치**로 최종 집계됩니다.")

    agents = get_agents()
    agent_map = {
        f"{a['slot']}. {a['title'] or a['name']}": a["slot"]
        for a in agents
    }

    selected_label = st.selectbox("평가할 Agent", list(agent_map.keys()))
    slot = agent_map[selected_label]
    selected_agent = next(a for a in agents if int(a["slot"]) == int(slot))

    render_agent_info(selected_agent)

    old = get_score(user, slot)
    defaults = [3, 3, 3, 3, 3]
    old_comment = ""

    if old:
        defaults = [int(old[f"c{i}"]) for i in range(1, 6)]
        old_comment = old.get("comment") or ""
        st.success("이미 제출한 Agent입니다. 다시 제출하면 기존 점수가 수정됩니다.")

    st.caption("1점 미흡 · 2점 다소 미흡 · 3점 보통 · 4점 우수 · 5점 매우 우수")

    values = []

    with st.form(f"score_form_{slot}"):
        for i, (name, description) in enumerate(CRITERIA):
            st.markdown(f"**{i + 1}. {name}**")
            st.caption(description)
            values.append(
                st.radio(
                    name,
                    [1, 2, 3, 4, 5],
                    index=defaults[i] - 1,
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"{user}_{slot}_c{i + 1}",
                )
            )

        comment = st.text_input(
            "한줄 의견 (선택)",
            value=old_comment,
            placeholder="Agent에 대한 의견이 있으면 입력",
        )
        submit_score = st.form_submit_button("✅ 점수 제출 / 수정", use_container_width=True)

    st.metric("입력 합계", f"{sum(values)} / 25점")

    if submit_score:
        try:
            save_score(user, slot, values, comment)
            st.success(f"{selected_label} 채점 완료 · {sum(values)}/25점")
        except Exception as e:
            st.error("저장 중 오류가 발생했습니다. 다시 제출해 주세요.")
            st.caption(str(e))

    rows = get_all_scores()
    done_slots = {
        int(r["agent_slot"])
        for r in rows
        if r.get("judge") == user
    }

    st.progress(len(done_slots) / 5)
    st.caption(f"내 채점 진행률: {len(done_slots)}/5 Agent 완료")
    st.stop()


# MASTER
st.success("MASTER 관리자 모드 · 실시간 집계")

tab_result, tab_status, tab_settings = st.tabs(
    ["📊 실시간 결과", "✅ 제출 현황", "⚙️ Agent 설정"]
)


def build_aggregate():
    agents = get_agents()
    score_df = pd.DataFrame(get_all_scores())

    base = pd.DataFrame(
        {
            "slot": [a["slot"] for a in agents],
            "Agent": [a["name"] for a in agents],
            "팀": [a["team"] for a in agents],
            "발표자": [a["presenter"] for a in agents],
            "제목": [a["title"] for a in agents],
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
        return base, score_df

    for i in range(1, 6):
        score_df[f"wc{i}"] = score_df[f"c{i}"] * score_df["weight"]

    agg = score_df.groupby("agent_slot", as_index=False).agg(
        현업문제=("wc1", "sum"),
        업무효과=("wc2", "sum"),
        완성도=("wc3", "sum"),
        활용편의=("wc4", "sum"),
        확산가능=("wc5", "sum"),
        최종점수=("weighted_total", "sum"),
        제출인원=("judge", "nunique"),
    )

    out = base.merge(agg, left_on="slot", right_on="agent_slot", how="left")
    out = out.drop(columns=["agent_slot"], errors="ignore").fillna(0)

    numeric = [
        "현업문제",
        "업무효과",
        "완성도",
        "활용편의",
        "확산가능",
        "최종점수",
        "제출인원",
    ]
    out[numeric] = out[numeric].astype(int)

    return out, score_df


with tab_result:

    @st.fragment(run_every="3s")
    def live_results():
        result, score_df = build_aggregate()

        result = result.sort_values(
            ["최종점수", "slot"],
            ascending=[False, True],
        ).reset_index(drop=True)

        result.insert(0, "순위", range(1, len(result) + 1))

        result["현재 수상"] = [
            "🥇 최우수" if i == 0
            else "🥈 우수" if i in (1, 2)
            else "🏅 장려"
            for i in range(len(result))
        ]

        completed_judges = 0
        if not score_df.empty:
            counts = score_df.groupby("judge")["agent_slot"].nunique()
            completed_judges = sum(int(counts.get(j, 0)) == 5 for j in JUDGES)

        m1, m2, m3 = st.columns(3)
        m1.metric("채점 완료 심사위원", f"{completed_judges} / 9")
        m2.metric("최종점수 만점", f"{MAX_TOTAL}점")
        m3.metric("자동 갱신", "3초")

        st.markdown("#### 🏆 종합 점수")

        st.dataframe(
            result[
                [
                    "순위",
                    "팀",
                    "발표자",
                    "제목",
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
            st.caption("※ 아직 모든 심사위원의 채점이 완료되지 않았으므로 순위는 변동될 수 있습니다.")
        else:
            st.success("9명 전원의 5개 Agent 채점이 완료되었습니다. 최종 결과를 확정할 수 있습니다.")

        render_podium(result)

        st.divider()
        st.markdown("#### 💬 입력된 심사위원 코멘트")
        st.caption("코멘트를 누르지 않아도 바로 읽을 수 있도록 전체 문장을 표시합니다.")

        agents = get_agents()
        title_map = {int(a["slot"]): a["title"] for a in agents}

        if score_df.empty or "comment" not in score_df.columns:
            st.info("아직 등록된 코멘트가 없습니다.")
            comments_df = pd.DataFrame()
        else:
            comments_df = score_df.copy()
            comments_df["comment"] = (
                comments_df["comment"]
                .fillna("")
                .astype(str)
                .str.strip()
            )
            comments_df = comments_df[comments_df["comment"] != ""].copy()

        if not comments_df.empty:
            comments_df["제목"] = comments_df["agent_slot"].astype(int).map(title_map)

            rank_map = {
                int(row["slot"]): int(row["순위"])
                for _, row in result.iterrows()
            }
            comments_df["rank"] = comments_df["agent_slot"].astype(int).map(rank_map).fillna(999)
            comments_df = comments_df.sort_values(["rank", "judge"])

            for _, row in comments_df.iterrows():
                render_comment_row(
                    row["제목"],
                    row["judge"],
                    row["total"],
                    row["weight"],
                    row["weighted_total"],
                    row["comment"],
                )

        st.divider()
        st.markdown("#### 🗂 Agent별 코멘트 모아보기")
        st.caption("Agent별로 심사 의견만 따로 모아서 확인할 수 있습니다.")

        for _, agent_row in result.iterrows():
            title = agent_row["제목"] or agent_row["Agent"]
            st.markdown(f"##### {title}")

            if comments_df.empty:
                st.caption("등록된 코멘트 없음")
                continue

            agent_comments = comments_df[
                comments_df["agent_slot"].astype(int) == int(agent_row["slot"])
            ]

            if agent_comments.empty:
                st.caption("등록된 코멘트 없음")
                continue

            for _, row in agent_comments.iterrows():
                render_comment_row(
                    title,
                    row["judge"],
                    row["total"],
                    row["weight"],
                    row["weighted_total"],
                    row["comment"],
                )

        st.divider()

        csv = result.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ 최종 결과 CSV 다운로드",
            data=csv,
            file_name="DIFFUSION_AX_최종결과.csv",
            mime="text/csv",
            use_container_width=True,
        )

    live_results()


with tab_status:

    @st.fragment(run_every="3s")
    def live_status():
        agents = get_agents()
        score_df = pd.DataFrame(get_all_scores())
        rows = []

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
                        (score_df["judge"] == judge)
                        &
                        (score_df["agent_slot"].astype(int) == int(agent["slot"]))
                    ).any()

                label = agent["title"] or agent["name"]
                row[label] = "✅" if done else "—"

            rows.append(row)

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        complete_count = 0 if score_df.empty else len(
            score_df.drop_duplicates(subset=["judge", "agent_slot"])
        )
        st.progress(min(complete_count / 45, 1.0))
        st.caption(f"전체 채점 진행률: {complete_count}/45")

    live_status()


with tab_settings:
    st.markdown("#### Agent 5개 발표 정보 설정")
    st.caption("팀 / 발표자 / 제목을 저장하면 모든 심사위원 채점 화면에 즉시 표시됩니다.")

    agents = get_agents()

    with st.form("agent_settings_form"):
        edited = {}

        for agent in agents:
            slot = int(agent["slot"])
            st.markdown(f"##### Agent {slot}")

            name = st.text_input(
                f"Agent {slot} 내부명",
                value=agent["name"],
                key=f"name_{slot}",
            )

            team = st.text_input(
                f"Agent {slot} 팀",
                value=agent["team"],
                placeholder="예: DRAM_ALD",
                key=f"team_{slot}",
            )

            presenter = st.text_input(
                f"Agent {slot} 발표자",
                value=agent["presenter"],
                placeholder="예: 홍길동",
                key=f"presenter_{slot}",
            )

            title = st.text_input(
                f"Agent {slot} 제목",
                value=agent["title"],
                placeholder="예: Trouble Guide Agent",
                key=f"title_{slot}",
            )

            edited[slot] = {
                "name": name,
                "team": team,
                "presenter": presenter,
                "title": title,
            }

            st.divider()

        save_agents = st.form_submit_button(
            "발표 정보 저장",
            use_container_width=True,
        )

    if save_agents:
        try:
            for slot, values in edited.items():
                update_agent(
                    slot,
                    values["name"],
                    values["team"],
                    values["presenter"],
                    values["title"],
                )

            st.success("5개 Agent 발표 정보가 저장되었습니다.")
            st.rerun()

        except Exception as e:
            st.error("발표 정보 저장에 실패했습니다.")
            st.caption(str(e))

    st.markdown("#### 행사 전 테스트 점수 초기화")
    confirm = st.checkbox("모든 채점 데이터 삭제에 동의합니다.")

    if st.button(
        "🗑️ 전체 점수 초기화",
        disabled=not confirm,
        use_container_width=True,
    ):
        try:
            clear_all_scores()
            st.success("모든 점수가 초기화되었습니다.")
            st.rerun()

        except Exception as e:
            st.error("초기화에 실패했습니다.")
            st.caption(str(e))

