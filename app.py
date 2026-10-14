import html
from datetime import datetime, timezone
from textwrap import dedent

import pandas as pd
import streamlit as st
from supabase import create_client

st.set_page_config(
    page_title="DIFFUSION AX CONTEST",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------
# 사용자 계정
# 필요시 비밀번호만 여기서 수정하세요.
# ---------------------------------------------------
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

# 심사위원 표시 순서
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

MAX_TOTAL = 25 * sum(USERS[j]["weight"] for j in JUDGES)

CRITERIA = [
    ("현업 문제 해결성", "실제 현장의 Pain Point / Needs를 제대로 해결하는가?"),
    ("업무 효과", "시간 단축 · 품질 향상 · Risk 감소 등 효과가 명확한가?"),
    ("Agent 완성도", "정확성 · 신뢰성이 실제 업무 활용 가능한 수준인가?"),
    ("활용 편의성", "쉽게 사용 가능하며 Legacy System / Data와 잘 연결되는가?"),
    ("확산 가능성", "다른 공정 · 팀에도 Skill / Tool / Agent 형태로 확산 가능한가?"),
]


# ---------------------------------------------------
# DB 연결
# Streamlit secrets 에 SUPABASE_URL / SUPABASE_KEY 필요
# ---------------------------------------------------
@st.cache_resource
def get_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


db = get_db()


# ---------------------------------------------------
# 공통 함수
# ---------------------------------------------------
def esc(v):
    return html.escape(str(v or ""))


def text_or(v, fallback=""):
    s = str(v or "").strip()
    return s if s else fallback


def html_block(markup: str):
    cleaned = "\n".join(line.lstrip() for line in dedent(markup).splitlines()).strip()
    st.markdown(cleaned, unsafe_allow_html=True)


def logout():
    st.session_state.clear()
    st.rerun()


# ---------------------------------------------------
# 데이터 함수
# ---------------------------------------------------
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
    out = []

    for slot in range(1, 6):
        r = by_slot.get(slot, {})
        out.append(
            {
                "slot": slot,
                "name": text_or(r.get("name"), f"Agent {slot}"),
                "team": text_or(r.get("team")),
                "presenter": text_or(r.get("presenter")),
                "title": text_or(r.get("title")),
            }
        )
    return out


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
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="judge,agent_slot",
    ).execute()


def update_agent(slot, name, team, presenter, title):
    db.table("agents").upsert(
        {
            "slot": slot,
            "name": text_or(name, f"Agent {slot}"),
            "team": text_or(team),
            "presenter": text_or(presenter),
            "title": text_or(title),
        },
        on_conflict="slot",
    ).execute()


def clear_all_scores():
    db.table("scores").delete().neq("judge", "__never__").execute()


def agent_title(agent):
    return text_or(agent.get("title"), f"Agent {agent['slot']}")


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
        for c in ["현업문제", "업무효과", "완성도", "활용편의", "확산가능", "최종점수", "제출인원"]:
            base[c] = 0
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

    nums = ["현업문제", "업무효과", "완성도", "활용편의", "확산가능", "최종점수", "제출인원"]
    out[nums] = out[nums].astype(int)

    return out, score_df


# ---------------------------------------------------
# 스타일
# ---------------------------------------------------
CSS = r"""
<style>
html, body, [data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 50% -10%, rgba(54,98,165,.20), transparent 35%),
    linear-gradient(180deg,#071522 0%,#04101b 58%,#020911 100%);
  color:#f5f7fb;
}

[data-testid="stHeader"] {
  background:rgba(2,8,15,.66);
  backdrop-filter:blur(8px);
}

.block-container {
  max-width:1500px;
  padding-top:2.2rem;
  padding-bottom:3rem;
}

.stButton button,
.stDownloadButton button {
  min-height:44px;
  border-radius:12px;
  font-weight:800;
}

div[data-testid="stTabs"] button {
  font-weight:800;
}

/* 상단 브랜드 */
.ax-brand {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  padding:16px 18px;
  margin-top:.2rem;
  margin-bottom:16px;
  border-radius:16px;
  border:1px solid rgba(130,164,206,.18);
  background:linear-gradient(90deg,rgba(12,31,53,.96),rgba(5,17,30,.95));
  box-shadow:0 12px 30px rgba(0,0,0,.22);
}
.ax-brand-title {
  font-size:1.18rem;
  font-weight:950;
  white-space:nowrap;
}
.ax-brand-title span {
  color:#7eaaff;
}
.ax-brand-user {
  color:#9dafc6;
  font-size:.86rem;
  white-space:nowrap;
}

/* Judge 선택 카드 */
.ax-agent-card {
  border:1px solid rgba(95,143,205,.24);
  border-radius:16px;
  padding:14px 16px;
  margin:8px 0 15px;
  background:linear-gradient(135deg,rgba(17,45,76,.92),rgba(8,25,45,.92));
}
.ax-agent-title {
  font-size:1.12rem;
  font-weight:950;
}
.ax-agent-meta {
  display:flex;
  gap:18px;
  flex-wrap:wrap;
  margin-top:8px;
  color:#b8c6d8;
}
.ax-agent-meta b {
  color:#fff;
}

/* 요약 지표 */
.ax-summary {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:10px;
  margin:8px 0 14px;
}
.ax-metric {
  border:1px solid rgba(130,164,206,.18);
  border-radius:15px;
  padding:13px 15px;
  background:linear-gradient(180deg,rgba(14,34,57,.94),rgba(6,20,36,.94));
}
.ax-metric-label {
  color:#9fb0c6;
  font-size:.73rem;
  font-weight:700;
}
.ax-metric-value {
  margin-top:4px;
  font-size:1.24rem;
  font-weight:950;
}

/* Awards */
.ax-awards {
  position:relative;
  overflow:hidden;
  border-radius:24px;
  padding:34px 18px 24px;
  border:1px solid rgba(225,179,58,.22);
  background:
    radial-gradient(circle at 50% 0%,rgba(79,135,213,.18),transparent 28%),
    radial-gradient(circle at 18% 0%,rgba(246,214,137,.12),transparent 24%),
    radial-gradient(circle at 82% 0%,rgba(246,214,137,.10),transparent 24%),
    linear-gradient(180deg,#0a1a2e 0%,#071321 58%,#040c16 100%);
  box-shadow:0 26px 60px rgba(0,0,0,.34);
}
.ax-awards-kicker {
  text-align:center;
  font-size:.72rem;
  letter-spacing:.22em;
  font-weight:900;
  color:#bdcbe0;
  margin-top:6px;
}
.ax-awards-title {
  text-align:center;
  margin:8px 0 2px;
  font-size:clamp(1.55rem,3.7vw,2.65rem);
  font-weight:1000;
  line-height:1;
}
.ax-awards-title span {
  display:block;
  margin-top:5px;
  font-size:1.14em;
  background:linear-gradient(180deg,#fff1a6,#e9b233 55%,#9c6207);
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent;
}
.ax-awards-sub {
  text-align:center;
  color:#a9b8cc;
  font-size:.83rem;
  margin:10px 0 28px;
}

.ax-podium-grid {
  display:grid;
  grid-template-columns:minmax(0,1fr) minmax(0,1.15fr) minmax(0,1fr);
  grid-template-areas:"silver gold bronze";
  gap:14px;
  align-items:end;
}
.ax-award-col {
  display:flex;
  flex-direction:column;
  justify-content:flex-end;
}
.ax-award-col.silver {
  grid-area:silver;
  margin-top:58px;
}
.ax-award-col.gold {
  grid-area:gold;
  margin-top:0;
}
.ax-award-col.bronze {
  grid-area:bronze;
  margin-top:88px;
}

.ax-award-head {
  display:flex;
  justify-content:center;
  align-items:center;
  gap:7px;
  font-weight:950;
  margin-bottom:10px;
  text-align:center;
}
.ax-medal {
  font-size:1.7rem;
}
.ax-award-name {
  font-size:1.05rem;
}
.ax-award-count {
  font-size:.70rem;
  color:#9fb0c6;
}
.ax-entry-list {
  display:grid;
  gap:9px;
}
.ax-entry {
  min-height:104px;
  display:flex;
  flex-direction:column;
  justify-content:center;
  padding:13px 11px;
  border-radius:15px;
  color:#102033;
  background:linear-gradient(180deg,rgba(245,248,252,.98),rgba(214,225,239,.98));
  border:1px solid rgba(255,255,255,.72);
  box-shadow:0 10px 24px rgba(0,0,0,.23);
}
.ax-gold-entry {
  min-height:126px;
  border:2px solid #efc351;
  box-shadow:0 0 30px rgba(240,181,44,.24),0 13px 30px rgba(0,0,0,.28);
}
.ax-entry.empty {
  opacity:.38;
}
.ax-team {
  font-weight:1000;
  font-size:1rem;
  overflow-wrap:anywhere;
}
.ax-presenter {
  font-size:.84rem;
  font-weight:800;
  margin-top:5px;
}
.ax-title {
  font-size:.74rem;
  color:#526277;
  margin-top:6px;
  line-height:1.35;
}

.ax-stage {
  margin-top:10px;
  border-radius:16px 16px 7px 7px;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:2rem;
  font-weight:1000;
  text-shadow:0 2px 8px rgba(0,0,0,.35);
  box-shadow:inset 0 1px rgba(255,255,255,.26),0 14px 28px rgba(0,0,0,.28);
}
.silver .ax-stage {
  height:86px;
  background:linear-gradient(180deg,#b9c2ce,#7d8999 52%,#4d5968);
  color:#fff;
}
.gold .ax-stage {
  height:140px;
  background:linear-gradient(180deg,#e8b735,#bb790b 52%,#744000);
  color:#fff8cf;
}
.bronze .ax-stage {
  height:68px;
  background:linear-gradient(180deg,#c87b3e,#8e4c21 52%,#5c3017);
  color:#ffe5c7;
}

/* 공통 섹션 */
.ax-section {
  margin-top:18px;
  border:1px solid rgba(130,164,206,.18);
  border-radius:18px;
  background:linear-gradient(180deg,rgba(11,28,49,.94),rgba(5,18,33,.94));
  padding:15px;
}
.ax-section-title {
  font-size:1.08rem;
  font-weight:950;
  margin-bottom:10px;
}
.ax-section-sub {
  font-size:.72rem;
  color:#9fb0c6;
  margin-left:6px;
}

/* 결과 표 */
.ax-table-wrap {
  overflow-x:auto;
  border-radius:13px;
  border:1px solid rgba(130,164,206,.18);
}
.ax-table {
  width:100%;
  min-width:980px;
  border-collapse:collapse;
  background:rgba(4,15,28,.75);
}
.ax-table th {
  background:#112945;
  color:#d8e4f2;
  padding:10px 8px;
  font-size:.75rem;
  text-align:center;
  border-bottom:1px solid rgba(130,164,206,.18);
  white-space:nowrap;
}
.ax-table td {
  padding:10px 8px;
  font-size:.81rem;
  text-align:center;
  color:#edf3fa;
  border-bottom:1px solid rgba(143,177,221,.09);
}
.ax-table tr.rank1 td {
  background:linear-gradient(90deg,rgba(217,167,40,.13),rgba(217,167,40,.03));
}
.ax-rank {
  display:inline-flex;
  width:29px;
  height:29px;
  border-radius:50%;
  align-items:center;
  justify-content:center;
  font-weight:1000;
  background:#1b314d;
}
.ax-rank.r1 {
  background:linear-gradient(135deg,#ffe487,#c98a0d);
  color:#291900;
}
.ax-rank.r2 {
  background:linear-gradient(135deg,#edf2f7,#8997a8);
  color:#13202e;
}
.ax-rank.r3 {
  background:linear-gradient(135deg,#e3a36e,#8f4a24);
  color:#261208;
}
.ax-left {
  text-align:left !important;
  max-width:280px;
}
.ax-team-cell {
  font-weight:950;
}

/* 코멘트 */
.ax-comments {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:10px;
}
.ax-comment {
  border:1px solid rgba(117,159,215,.18);
  border-radius:14px;
  padding:13px 14px;
  min-height:126px;
  background:linear-gradient(180deg,rgba(13,31,54,.92),rgba(6,20,36,.92));
}
.ax-comment.champion {
  border-color:rgba(240,190,60,.5);
  box-shadow:inset 0 0 0 1px rgba(240,190,60,.08);
}
.ax-comment-top {
  display:flex;
  justify-content:space-between;
  gap:10px;
  margin-bottom:8px;
}
.ax-judge {
  font-weight:950;
  color:#9ec0ff;
}
.ax-comment.champion .ax-judge {
  color:#ffd86d;
}
.ax-agent {
  font-size:.69rem;
  color:#91a2b7;
  text-align:right;
}
.ax-comment-body {
  font-size:.87rem;
  line-height:1.5;
  color:#edf3f9;
  white-space:pre-wrap;
  word-break:break-word;
}
.ax-comment-score {
  font-size:.69rem;
  color:#7f93ad;
  margin-top:10px;
}

/* 태블릿 */
@media(max-width:1099px){
  .ax-podium-grid{gap:8px}
  .ax-entry{padding:10px 7px;min-height:96px}
  .ax-gold-entry{min-height:112px}
  .ax-team{font-size:.84rem}
  .ax-presenter{font-size:.73rem}
  .ax-title{font-size:.64rem}
  .ax-comments{grid-template-columns:repeat(2,minmax(0,1fr))}
  .silver .ax-stage{height:78px}
  .gold .ax-stage{height:126px}
  .bronze .ax-stage{height:62px}
}

/* 모바일 */
@media(max-width:699px){
  .block-container{
    padding-top:1.7rem;
    padding-left:.7rem;
    padding-right:.7rem;
  }
  .ax-brand-user{display:none}
  .ax-summary{grid-template-columns:1fr;gap:7px}
  .ax-awards{padding:24px 10px 18px}
  .ax-podium-grid{
    grid-template-columns:1fr;
    grid-template-areas:"gold" "silver" "bronze";
    gap:18px;
  }
  .ax-award-col{
    max-width:520px;
    width:100%;
    margin:0 auto !important;
  }
  .ax-stage{height:48px !important;font-size:1.5rem}
  .gold .ax-stage{height:70px !important}
  .ax-entry,.ax-gold-entry{min-height:auto}
  .ax-comments{grid-template-columns:1fr}
  .ax-section{padding:12px}
  .ax-table{min-width:860px}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------
# 렌더 함수
# ---------------------------------------------------
def render_brand(user=None):
    who = f"접속자 · {esc(user)}" if user else "모바일 실시간 채점 시스템"
    html_block(
        f"""
        <div class="ax-brand">
          <div class="ax-brand-title">DIFFUSION <span>AX</span> CONTEST</div>
          <div class="ax-brand-user">{who}</div>
        </div>
        """
    )


def render_agent_card(agent):
    html_block(
        f"""
        <div class="ax-agent-card">
          <div class="ax-agent-title">{esc(agent_title(agent))}</div>
          <div class="ax-agent-meta">
            <span><b>팀</b> {esc(text_or(agent.get('team'), '팀 미입력'))}</span>
            <span><b>발표자</b> {esc(text_or(agent.get('presenter'), '발표자 미입력'))}</span>
          </div>
        </div>
        """
    )


def award_entry(row, gold=False):
    if row is None:
        return '<div class="ax-entry empty"><div class="ax-team">&nbsp;</div><div class="ax-presenter">&nbsp;</div><div class="ax-title">&nbsp;</div></div>'

    cls = "ax-entry ax-gold-entry" if gold else "ax-entry"
    team = text_or(row.get("팀"), "팀 미입력")
    presenter = text_or(row.get("발표자"), "발표자 미입력")
    title = text_or(row.get("제목"), f"Agent {int(row.get('slot', 0))}")

    return (
        f'<div class="{cls}">'
        f'<div class="ax-team">{esc(team)}</div>'
        f'<div class="ax-presenter">{esc(presenter)}</div>'
        f'<div class="ax-title">{esc(title)}</div>'
        f'</div>'
    )


def render_summary(completed_judges, complete_count):
    html_block(
        f"""
        <div class="ax-summary">
          <div class="ax-metric">
            <div class="ax-metric-label">채점 완료 심사위원</div>
            <div class="ax-metric-value">{completed_judges} / 9</div>
          </div>
          <div class="ax-metric">
            <div class="ax-metric-label">전체 채점 진행</div>
            <div class="ax-metric-value">{complete_count} / 45</div>
          </div>
          <div class="ax-metric">
            <div class="ax-metric-label">Agent 최종점수 만점</div>
            <div class="ax-metric-value">{MAX_TOTAL}점</div>
          </div>
        </div>
        """
    )


def render_awards(result):
    rec = result.to_dict("records")
    first = rec[0] if len(rec) >= 1 else None
    silver = rec[1:3] + [None] * max(0, 2 - len(rec[1:3]))
    bronze = rec[3:5] + [None] * max(0, 2 - len(rec[3:5]))

    html_block(
        f"""
        <div class="ax-awards">
          <div class="ax-awards-kicker">DIFFUSION AX CONTEST</div>
          <div class="ax-awards-title">🏆<span>AWARDS</span></div>
          <div class="ax-awards-sub">혁신의 아이디어가 더 나은 현장을 만듭니다</div>

          <div class="ax-podium-grid">
            <div class="ax-award-col silver">
              <div class="ax-award-head">
                <span class="ax-medal">🥈</span>
                <span class="ax-award-name">우수상</span>
                <span class="ax-award-count">2팀</span>
              </div>
              <div class="ax-entry-list">
                {award_entry(silver[0])}
                {award_entry(silver[1])}
              </div>
              <div class="ax-stage">2</div>
            </div>

            <div class="ax-award-col gold">
              <div class="ax-award-head">
                <span class="ax-medal">🥇</span>
                <span class="ax-award-name">최우수상</span>
                <span class="ax-award-count">1팀</span>
              </div>
              <div class="ax-entry-list">
                {award_entry(first, gold=True)}
              </div>
              <div class="ax-stage">1</div>
            </div>

            <div class="ax-award-col bronze">
              <div class="ax-award-head">
                <span class="ax-medal">🥉</span>
                <span class="ax-award-name">장려상</span>
                <span class="ax-award-count">2팀</span>
              </div>
              <div class="ax-entry-list">
                {award_entry(bronze[0])}
                {award_entry(bronze[1])}
              </div>
              <div class="ax-stage">3</div>
            </div>
          </div>
        </div>
        """
    )


def render_result_table(result):
    rows = []

    for _, r in result.iterrows():
        rank = int(r["순위"])

        if rank == 1:
            rc, award, tr = "r1", "🥇 최우수", "rank1"
        elif rank in (2, 3):
            rc, award, tr = "r2", "🥈 우수", ""
        else:
            rc, award, tr = "r3", "🥉 장려", ""

        rows.append(
            f"""
            <tr class="{tr}">
              <td><span class="ax-rank {rc}">{rank}</span></td>
              <td class="ax-team-cell">{esc(text_or(r['팀']))}</td>
              <td>{esc(text_or(r['발표자']))}</td>
              <td class="ax-left">{esc(text_or(r['제목']))}</td>
              <td><b>{int(r['최종점수'])}</b></td>
              <td>{award}</td>
              <td>{int(r['제출인원'])}/9</td>
              <td>{int(r['현업문제'])}</td>
              <td>{int(r['업무효과'])}</td>
              <td>{int(r['완성도'])}</td>
              <td>{int(r['활용편의'])}</td>
              <td>{int(r['확산가능'])}</td>
            </tr>
            """
        )

    html_block(
        f"""
        <div class="ax-section">
          <div class="ax-section-title">📊 최종 결과표 <span class="ax-section-sub">가중치 반영 실시간 집계</span></div>
          <div class="ax-table-wrap">
            <table class="ax-table">
              <thead>
                <tr>
                  <th>순위</th>
                  <th>팀</th>
                  <th>발표자</th>
                  <th>제목</th>
                  <th>총점</th>
                  <th>현재 수상</th>
                  <th>제출</th>
                  <th>현업문제</th>
                  <th>업무효과</th>
                  <th>완성도</th>
                  <th>활용편의</th>
                  <th>확산가능</th>
                </tr>
              </thead>
              <tbody>
                {''.join(rows)}
              </tbody>
            </table>
          </div>
        </div>
        """
    )


def render_comments(comments_df, result):
    if comments_df.empty:
        html_block(
            """
            <div class="ax-section">
              <div class="ax-section-title">💬 심사위원 코멘트</div>
              <div style="color:#9fb0c6;font-size:.85rem">아직 등록된 코멘트가 없습니다.</div>
            </div>
            """
        )
        return

    agent_map = {
        int(r["slot"]): {
            "team": text_or(r["팀"]),
            "title": text_or(r["제목"], f"Agent {int(r['slot'])}"),
        }
        for _, r in result.iterrows()
    }

    comments = comments_df.copy()
    comments["judge_order"] = comments["judge"].map(JUDGE_ORDER).fillna(999)
    comments = comments.sort_values(["judge_order", "agent_slot"])

    cards = []
    for _, r in comments.iterrows():
        slot = int(r["agent_slot"])
        info = agent_map.get(slot, {"team": "", "title": f"Agent {slot}"})
        is_champion = r["judge"] == "DIFF_CHAMPION"
        cls = " champion" if is_champion else ""
        crown = "👑 " if is_champion else ""

        cards.append(
            f"""
            <div class="ax-comment{cls}">
              <div class="ax-comment-top">
                <div class="ax-judge">{crown}{esc(r['judge'])}</div>
                <div class="ax-agent">{esc(info['team'])}<br>{esc(info['title'])}</div>
              </div>
              <div class="ax-comment-body">{esc(r['comment'])}</div>
              <div class="ax-comment-score">원점수 {int(r['total'])}/25 · 가중치 ×{int(r['weight'])} · 반영 {int(r['weighted_total'])}점</div>
            </div>
            """
        )

    html_block(
        f"""
        <div class="ax-section">
          <div class="ax-section-title">💬 심사위원 코멘트 <span class="ax-section-sub">DIFF_CHAMPION → DIFF_STRAT → 나머지 ABC 순</span></div>
          <div class="ax-comments">
            {''.join(cards)}
          </div>
        </div>
        """
    )


# ---------------------------------------------------
# 로그인 화면
# ---------------------------------------------------
if "user" not in st.session_state:
    render_brand()

    _, center, _ = st.columns([1, 1.25, 1])
    with center:
        st.markdown("### 🏆 DIFFUSION AX 경진대회")
        st.caption("심사위원 또는 MASTER 계정으로 로그인하세요.")

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


# ---------------------------------------------------
# 로그인 후 공통 헤더
# ---------------------------------------------------
user = st.session_state["user"]
role = st.session_state["role"]

render_brand(user)

spacer_col, logout_col = st.columns([8, 1])
with logout_col:
    if st.button("로그아웃", use_container_width=True):
        logout()


# ---------------------------------------------------
# 심사위원 화면
# ---------------------------------------------------
if role == "judge":
    weight = USERS[user]["weight"]

    if weight == 3:
        st.warning("DIFF_CHAMPION 채점은 **3배 가중치**로 최종 집계됩니다.")
    else:
        st.info("채점 결과는 **1배 가중치**로 최종 집계됩니다.")

    agents = get_agents()
    agent_map = {f"{a['slot']}. {agent_title(a)}": a["slot"] for a in agents}
    selected_label = st.selectbox("평가할 Agent", list(agent_map.keys()))
    slot = agent_map[selected_label]
    selected_agent = next(a for a in agents if int(a["slot"]) == int(slot))

    render_agent_card(selected_agent)

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
        for i, (name, desc) in enumerate(CRITERIA):
            st.markdown(f"**{i+1}. {name}**")
            st.caption(desc)
            values.append(
                st.radio(
                    name,
                    [1, 2, 3, 4, 5],
                    index=defaults[i] - 1,
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"{user}_{slot}_c{i+1}",
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
        except Exception as ex:
            st.error("저장 중 오류가 발생했습니다. 다시 제출해 주세요.")
            st.caption(str(ex))

    rows = get_all_scores()
    done_slots = {int(r["agent_slot"]) for r in rows if r.get("judge") == user}
    st.progress(len(done_slots) / 5)
    st.caption(f"내 채점 진행률: {len(done_slots)}/5 Agent 완료")
    st.stop()


# ---------------------------------------------------
# MASTER 화면
# ---------------------------------------------------
st.success("MASTER 관리자 모드 · 실시간 집계")

tab_result, tab_status, tab_settings = st.tabs(
    ["🏆 결과 보기", "✅ 제출 현황", "⚙️ Agent 설정"]
)

with tab_result:
    @st.fragment(run_every="3s")
    def live_results():
        result, score_df = build_aggregate()
        result = result.sort_values(["최종점수", "slot"], ascending=[False, True]).reset_index(drop=True)
        result.insert(0, "순위", range(1, len(result) + 1))

        complete_count = 0
        completed_judges = 0

        if not score_df.empty:
            unique_scores = score_df.drop_duplicates(subset=["judge", "agent_slot"])
            complete_count = len(unique_scores)
            counts = unique_scores.groupby("judge")["agent_slot"].nunique()
            completed_judges = sum(int(counts.get(j, 0)) == 5 for j in JUDGES)

        render_summary(completed_judges, complete_count)
        render_awards(result)
        render_result_table(result)

        if completed_judges < 9:
            st.caption("※ 아직 모든 심사위원의 채점이 완료되지 않아 순위가 변동될 수 있습니다.")
        else:
            st.success("9명 전원의 5개 Agent 채점이 완료되었습니다. 최종 결과를 확정할 수 있습니다.")

        comments_df = pd.DataFrame()
        if not score_df.empty and "comment" in score_df.columns:
            comments_df = score_df.copy()
            comments_df["comment"] = comments_df["comment"].fillna("").astype(str).str.strip()
            comments_df = comments_df[comments_df["comment"] != ""].copy()

        render_comments(comments_df, result)

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
            row = {"심사위원": judge, "가중치": USERS[judge]["weight"]}

            for agent in agents:
                if score_df.empty:
                    done = False
                else:
                    done = (
                        (score_df["judge"] == judge)
                        & (score_df["agent_slot"].astype(int) == int(agent["slot"]))
                    ).any()

                row[agent_title(agent)] = "✅" if done else "—"

            rows.append(row)

        st.markdown("### ✅ 제출 현황")
        st.caption("DIFF_CHAMPION → DIFF_STRAT → 나머지 ABC 순")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        complete_count = 0 if score_df.empty else len(score_df.drop_duplicates(subset=["judge", "agent_slot"]))
        st.progress(min(complete_count / 45, 1.0))
        st.caption(f"전체 채점 진행률: {complete_count}/45")

    live_status()


with tab_settings:
    st.markdown("### ⚙️ Agent 발표 정보 설정")
    st.caption("팀 / 발표자 / 제목을 입력하면 포디움·결과표·심사위원 화면에 즉시 반영됩니다.")

    agents = get_agents()

    with st.form("agent_settings_form"):
        edited = {}

        for agent in agents:
            slot = int(agent["slot"])
            st.markdown(f"#### Agent {slot}")

            name = st.text_input(
                f"Agent {slot} 내부명",
                value=agent["name"],
                key=f"name_{slot}",
            )

            c1, c2 = st.columns(2)
            with c1:
                team = st.text_input(
                    f"Agent {slot} 팀",
                    value=agent["team"],
                    placeholder="예: DRAM_ALD",
                    key=f"team_{slot}",
                )
            with c2:
                presenter = st.text_input(
                    f"Agent {slot} 발표자",
                    value=agent["presenter"],
                    placeholder="예: 홍길동",
                    key=f"presenter_{slot}",
                )

            title = st.text_input(
                f"Agent {slot} 제목",
                value=agent["title"],
                placeholder="예: DORIS Super Agent",
                key=f"title_{slot}",
            )

            edited[slot] = {
                "name": name,
                "team": team,
                "presenter": presenter,
                "title": title,
            }

            st.divider()

        save_agents = st.form_submit_button("💾 발표 정보 저장", use_container_width=True)

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
        except Exception as ex:
            st.error("발표 정보 저장에 실패했습니다.")
            st.caption(str(ex))

    st.divider()
    st.markdown("### 🗑 행사 전 테스트 점수 초기화")
    confirm = st.checkbox("모든 채점 데이터 삭제에 동의합니다.")

    if st.button("전체 점수 초기화", disabled=not confirm, use_container_width=True):
        try:
            clear_all_scores()
            st.success("모든 점수가 초기화되었습니다.")
            st.rerun()
        except Exception as ex:
            st.error("초기화에 실패했습니다.")
            st.caption(str(ex))
