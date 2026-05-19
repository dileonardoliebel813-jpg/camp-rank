import { useMemo, useState } from "react";

const TRUST_POINTS = [
  ["只看预算内", "先按你填写的预算排除不合适价格，不把超预算商品塞进前三。"],
  ["优先满足核心需求", "场景和多选侧重点会一起参与筛选，完全满足的商品优先展示。"],
  ["不补造缺失参数", "重量、防水、收纳等页面没有给出的信息，会标成待确认。"],
];

const SCENARIO_OPTIONS = [
  {
    id: "weekend_park",
    label: "短途休闲露营",
    desc: "公园、野餐、半天到一天使用",
    scenario: "newbie_weekend",
  },
  {
    id: "family",
    label: "家庭亲子露营",
    desc: "更看重空间、搭建和舒适度",
    scenario: "family_camping",
  },
  {
    id: "overnight",
    label: "短途过夜露营",
    desc: "需要更谨慎看防水和稳定性",
    scenario: "overnight",
  },
  {
    id: "rain",
    label: "雨天/潮湿备用",
    desc: "重点看防水、防风和相关差评",
    scenario: "rain_backup",
  },
  {
    id: "group",
    label: "多人聚会/大空间",
    desc: "优先空间面积和容量描述",
    scenario: "group_party",
  },
  {
    id: "carry_light",
    label: "步行携带/收纳",
    desc: "重点看重量和收纳尺寸",
    scenario: "hiking_lightweight",
  },
];

const CONCERN_OPTIONS = [
  {
    id: "risk_control",
    label: "综合风险控制",
    desc: "价格、评论、售后一起看",
    preference: "balanced",
  },
  {
    id: "price_priority",
    label: "到手价优先",
    desc: "预算紧，先看低价区间",
    preference: "lowest_price",
  },
  {
    id: "after_sale",
    label: "售后退换保障",
    desc: "更看重退换、退款和售后风险",
    preference: "after_sale",
  },
  {
    id: "space",
    label: "容量与空间",
    desc: "更看重展开面积和人数匹配",
    preference: "gift_package",
  },
  {
    id: "portable",
    label: "收纳携带负担",
    desc: "缺重量/收纳参数不会当轻便",
    preference: "portable",
  },
  {
    id: "weather",
    label: "防水/防风反馈",
    desc: "结合页面参数和评论风险",
    preference: "weather_protection",
  },
  {
    id: "easy_setup",
    label: "搭建复杂度",
    desc: "新手更适合速开、自动、弹压",
    preference: "easy_setup",
  },
  {
    id: "less_stuffy",
    label: "闷热/异味反馈",
    desc: "更关注透气和气味相关评论",
    preference: "less_stuffy",
  },
];

function selectedConcernOptions(filters) {
  return CONCERN_OPTIONS.filter((option) => filters.concern_answers.includes(option.id));
}

function requestPayload(filters) {
  const selectedOptions = selectedConcernOptions(filters);
  return {
    ...filters,
    preference: selectedOptions.map((option) => option.preference).join(",") || "balanced",
  };
}

export default function Home({ onStart }) {
  const [filters, setFilters] = useState({
    min_price: 100,
    max_price: 1000,
    scenario: "newbie_weekend",
    scenario_answer: "weekend_park",
    preference: "balanced",
    concern_answers: ["risk_control"],
    limit: 50,
  });

  const activeScenario = useMemo(
    () => SCENARIO_OPTIONS.find((option) => option.id === filters.scenario_answer) || SCENARIO_OPTIONS[0],
    [filters.scenario_answer],
  );

  const activeConcerns = useMemo(() => selectedConcernOptions(filters), [filters]);

  const summaryText = useMemo(() => {
    const concernText = activeConcerns.map((option) => option.label).join("、") || "综合风险控制";
    return `将按：${filters.min_price || 0}-${filters.max_price || 0} 元 / ${activeScenario.label} / ${concernText} 筛选。`;
  }, [activeConcerns, activeScenario.label, filters.max_price, filters.min_price]);

  function updateFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function chooseScenario(option) {
    setFilters((current) => ({
      ...current,
      scenario: option.scenario,
      scenario_answer: option.id,
    }));
  }

  function chooseConcern(option) {
    setFilters((current) => ({
      ...current,
      concern_answers: (() => {
        const currentAnswers = Array.isArray(current.concern_answers) ? current.concern_answers : [];
        if (option.id === "risk_control") return ["risk_control"];
        const baseAnswers = currentAnswers.filter((id) => id !== "risk_control");
        const nextAnswers = baseAnswers.includes(option.id)
          ? baseAnswers.filter((id) => id !== option.id)
          : [...baseAnswers, option.id];
        return nextAnswers.length ? nextAnswers : ["risk_control"];
      })(),
    }));
  }

  function submit(event) {
    event.preventDefault();
    onStart(requestPayload(filters));
  }

  return (
    <section className="home-screen">
      <div className="home-primary">
        <p className="eyebrow">CampRank 购买助手</p>
        <h1>先选用途，再看 3 个购买方案</h1>
        <p className="lead">
          按预算、使用场景和你最在意的问题筛一遍。系统会优先展示完全满足核心要求的商品；
          不足 3 款时，会用部分匹配补位并说明原因。
        </p>

        <form className="demo-control" onSubmit={submit}>
          <div className="control-header">
            <div>
              <p className="eyebrow">开始筛选</p>
              <h2>告诉我你的预算和用途</h2>
            </div>
            <span>选好后生成 3 个方案</span>
          </div>

          <div className="field-row">
            <label>
              最低预算
              <input
                type="number"
                min="0"
                value={filters.min_price}
                onChange={(event) => updateFilter("min_price", event.target.value)}
              />
            </label>
            <label>
              最高预算
              <input
                type="number"
                min="0"
                value={filters.max_price}
                onChange={(event) => updateFilter("max_price", event.target.value)}
              />
            </label>
          </div>

          <fieldset>
            <legend>使用场景（单选）</legend>
            <div className="segmented question-grid">
              {SCENARIO_OPTIONS.map((option) => (
                <label key={option.id} className={filters.scenario_answer === option.id ? "selected" : ""}>
                  <input
                    type="radio"
                    name="scenario"
                    value={option.id}
                    checked={filters.scenario_answer === option.id}
                    onChange={() => chooseScenario(option)}
                  />
                  <span className="option-title">{option.label}</span>
                  <span className="option-desc">{option.desc}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend>购买侧重点（可多选）</legend>
            <div className="segmented question-grid concern-grid">
              {CONCERN_OPTIONS.map((option) => (
                <label key={option.id} className={filters.concern_answers.includes(option.id) ? "selected" : ""}>
                  <input
                    type="checkbox"
                    name="concern"
                    value={option.id}
                    checked={filters.concern_answers.includes(option.id)}
                    onChange={() => chooseConcern(option)}
                  />
                  <span className="option-title">{option.label}</span>
                  <span className="option-desc">{option.desc}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="home-submit-row">
            <p>{summaryText}</p>
            <button type="submit" className="wide-button primary-cta">
              <span>生成 3 个购买方案</span>
              <small>按当前选择开始筛选</small>
            </button>
          </div>
        </form>
      </div>

      <aside className="home-aside" aria-label="筛选说明">
        <div className="home-photo">
          <img
            src="https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?auto=format&fit=crop&w=1100&q=82"
            alt="户外帐篷内看向树林"
          />
        </div>
        <div className="home-proof">
          <p className="eyebrow">结果怎么判断</p>
          <h2>不是只挑最便宜，也不替商品页补参数</h2>
          <p className="muted">
            推荐会同时看价格、评论风险、售后文本和已接入的商品参数。页面没有写清楚的重量、防水或收纳信息，会直接提示你下单前确认。
          </p>
          <div className="promise-list">
            {TRUST_POINTS.map(([title, body], index) => (
              <div key={title}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{title}</strong>
                <p>{body}</p>
              </div>
            ))}
          </div>
          <p className="home-proof-note">完成左侧选择后，点击绿色按钮生成结果。</p>
        </div>
      </aside>
    </section>
  );
}
