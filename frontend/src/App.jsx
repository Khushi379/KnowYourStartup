import { useMemo, useState, useEffect } from "react";

const initialForm = {
  project_name: "ForgeLink AI",
  idea_summary:
    "A platform that helps founders and hackathon teams turn raw ideas into validated MVP plans by matching problem urgency, market timing, and AI-assisted product strategy.",
  domain: "general",
  team_skills: "frontend, backend, ai, design",
};

function resolveApiBase() {
  if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
  if (typeof window !== "undefined") {
    const { hostname, origin } = window.location;
    if (hostname === "localhost" || hostname === "127.0.0.1") return "http://127.0.0.1:8100";
    return origin;
  }
  return "";
}

const apiBase = resolveApiBase();

const domainLabels = {
  general: "General innovation",
  education: "Education",
  health: "Health",
  sustainability: "Sustainability",
  finance: "Finance",
  media: "Media",
  community: "Community",
  developer_tools: "Developer tools",
};

function getScoreBand(score) {
  if (score >= 8) return "High";
  if (score >= 5) return "Medium";
  return "Low";
}

function getScoreBandClass(score) {
  return `score-band ${getScoreBand(score).toLowerCase()}`;
}

function App() {
  const [page, setPage] = useState("landing");
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const skills = useMemo(
    () => form.team_skills.split(",").map((s) => s.trim()).filter(Boolean),
    [form.team_skills]
  );

  const dashboardSignals = [
    { label: "Selected domain", value: domainLabels[form.domain] },
    { label: "Founder brief", value: `${form.idea_summary.split(/\s+/).filter(Boolean).length} words` },
    { label: "Team skills", value: `${skills.length} listed` },
  ];

  const ideaPrompts = ["Who has the problem?", "Why is it painful right now?", "What is the smallest useful solution?"];

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [page]);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${apiBase}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, team_skills: skills }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Backend error (${response.status})`);
      }

      const data = await response.json();
      setResult(data);
      setPage("output");
    } catch (err) {
      setError(err.message || "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  // ── Derive roadmap and architecture from API result, never hardcoded ──
  const roadmap = result?.roadmap ?? [];
  const architectureBlocks = result?.architecture_blocks ?? [];

  return (
    <div className="shell">
      <div className="mesh mesh-a" />
      <div className="mesh mesh-b" />

      <main className="layout">
        {/* ── Topbar ── */}
        <div className="topbar">
          <div className="brand-mark"><h2>ForgeLink AI</h2></div>
          <div className="step-tabs">
            <button className={`step-tab ${page === "landing" ? "active" : ""}`} type="button" onClick={() => setPage("landing")}>
              Intro
            </button>
            <button className={`step-tab ${page === "input" ? "active" : ""}`} type="button" onClick={() => setPage("input")}>
              Input
            </button>
            <button
              className={`step-tab ${page === "output" ? "active" : ""}`}
              type="button"
              onClick={() => result && setPage("output")}
              disabled={!result}
            >
              Output
            </button>
          </div>
        </div>

        {/* ── Landing ── */}
        {page === "landing" && (
          <section className="landing-screen panel">
            <div className="landing-copy">
              <div className="tag" />
              <h1>ForgeLink AI</h1>
              <p>
                An AI innovation copilot that transforms raw ideas into actionable opportunity scores,
                operator-grade insights, and clear MVP roadmaps.
              </p>
              <div className="hero-cards">
                <article>
                  <h3>Score startup potential</h3>
                  <p>Read the founder brief like an operator instead of asking users to fill in scoring sliders.</p>
                </article>
                <article>
                  <h3>Show the operator thesis</h3>
                  <p>Return a concise memo with what works, what breaks, and what to do next.</p>
                </article>
                <article>
                  <h3>Get an implementation roadmap</h3>
                  <p>Turn the project summary into practical build phases for a real MVP.</p>
                </article>
              </div>
              <button className="primary landing-cta" type="button" onClick={() => setPage("input")} style={{ marginTop: "20px" }}>
                <span className="button-label">Get Started</span>
              </button>
            </div>

            <aside className="hero-side hero-visual" aria-hidden="true">
              <div className="orbit orbit-a" />
              <div className="orbit orbit-b" />
              <div className="orbit orbit-c" />
              <div className="pulse-core">
                <span>Operator Mode</span>
                <strong>Live scoring flow</strong>
              </div>
              <div className="signal-trail signal-trail-a" />
              <div className="signal-trail signal-trail-b" />
            </aside>
          </section>
        )}

        {/* ── Input ── */}
        {page === "input" && (
          <section className="single-page">
            <form className="panel form-panel" onSubmit={handleSubmit}>
              <div className="heading">
                <h2>Describe the product you want to build</h2>
              </div>

              <div className="input-dashboard">
                <section className="dashboard-block accent-block">
                  <div className="block-head">
                    <div>
                      <span>Founder Brief</span>
                      <h3>Start with the project summary</h3>
                    </div>
                    <div className="signal-pills">
                      {dashboardSignals.map((signal) => (
                        <div className="signal-pill" key={signal.label}>
                          <span>{signal.label}</span>
                          <strong>{signal.value}</strong>
                        </div>
                      ))}
                    </div>
                  </div>

                  <label>
                    Startup Name
                    <input name="project_name" value={form.project_name} onChange={updateField} />
                  </label>

                  <label>
                    Startup Summary
                    <textarea name="idea_summary" rows="6" value={form.idea_summary} onChange={updateField} />
                  </label>

                  <div className="summary-helper">
                    <span>Write it like this:</span>
                    <p>Who has the problem, what pain they feel, and how your product solves it better.</p>
                  </div>

                  <div className="prompt-chip-row">
                    {ideaPrompts.map((prompt) => (
                      <span className="prompt-chip" key={prompt}>{prompt}</span>
                    ))}
                  </div>
                </section>

                <section className="dashboard-block">
                  <div className="block-head">
                    <div>
                      <h3>Pick the market and define the builder context</h3>
                    </div>
                  </div>

                  <div className="two-col">
                    <label>
                      Domain
                      <select name="domain" value={form.domain} onChange={updateField}>
                        <option value="general">General</option>
                        <option value="education">Education</option>
                        <option value="health">Health</option>
                        <option value="sustainability">Sustainability</option>
                        <option value="finance">Finance</option>
                        <option value="media">Media</option>
                        <option value="community">Community</option>
                        <option value="developer_tools">Developer Tools</option>
                      </select>
                    </label>

                    <label>
                      Team skills
                      <input name="team_skills" value={form.team_skills} onChange={updateField} />
                    </label>
                  </div>

                  <div className="context-card">
                    <span>Current focus</span>
                    <strong>{domainLabels[form.domain]}</strong>
                    <p>The backend will score this like an operator from the founder brief, domain, and listed team strengths.</p>
                  </div>

                  <div className="skill-chip-row">
                    {skills.map((skill) => (
                      <span className="skill-chip" key={skill}>{skill}</span>
                    ))}
                  </div>
                </section>
              </div>

              <div className="page-actions">
                <button className="secondary" type="button" onClick={() => setPage("landing")}>Back</button>
                <button className={`primary ${loading ? "is-loading" : ""}`} type="submit" disabled={loading}>
                  <span className="button-label">{loading ? "Scoring Idea..." : "Know your StartUp"}</span>
                </button>
              </div>

              {error && <p className="error">{error}</p>}
            </form>
          </section>
        )}

        {/* ── Output ── */}
        {page === "output" && (
          <section className="single-page">
            <section className="panel output-panel">
              <div className="heading">
                <h2>Operator score and execution view</h2>
              </div>

              {!result ? (
                <div className="empty">
                  <p>Generate a report first to view the output page.</p>
                </div>
              ) : (
                <div className="results">
                  <div className="page-actions">
                    <button className="secondary" type="button" onClick={() => setPage("input")}>Edit Input</button>
                  </div>

                  {/* Score row */}
                  <div className="score-row compact">
                    <article className="score primary-score wide">
                      <span>Operator score</span>
                      <strong>{result.innovation_score}</strong>
                      <h2>{result.verdict}</h2>
                    </article>
                    <article className="score">
                      <span>Operator read</span>
                      <strong>{Math.round(result.innovation_score / 10)}/10</strong>
                      <p>{result.operator_summary}</p>
                    </article>
                  </div>

                  {/* Summary */}
                  <div className="story">
                    <h3>Summary</h3>
                    <p>{result.summary}</p>
                    <p className="statement">{result.opportunity_statement}</p>
                  </div>

                  {/* Operator report */}
                  <div className="ai-brief">
                    <div className="section-bar">
                      <h3>Operator Report</h3>
                    </div>
                    <pre className="report-block">{result.operator_report}</pre>
                  </div>

                  {/* Score breakdown */}
                  <div className="card-list">
                    <h3>Score breakdown</h3>
                    <div className="breakdown-grid">
                      {result.score_breakdown.map((item) => (
                        <article className="breakdown-card" key={item.key}>
                          <span>{item.label}</span>
                          <strong>{item.score}/10</strong>
                          <div className={getScoreBandClass(item.score)}>{getScoreBand(item.score)}</div>
                          <p>{item.rationale}</p>
                        </article>
                      ))}
                    </div>
                  </div>

                  {/* Strengths / Risks */}
                  <div className="columns">
                    <div className="card-list">
                      <h3>Strengths</h3>
                      <ul>{result.strengths.map((item) => <li key={item}>{item}</li>)}</ul>
                    </div>
                    <div className="card-list">
                      <h3>Risks</h3>
                      <ul>{result.risks.map((item) => <li key={item}>{item}</li>)}</ul>
                    </div>
                  </div>

                  {/* MVP features / Target users */}
                  <div className="columns">
                    <div className="card-list">
                      <h3>MVP features</h3>
                      <ul>{result.mvp_features.map((item) => <li key={item}>{item}</li>)}</ul>
                    </div>
                    <div className="card-list">
                      <h3>Target users</h3>
                      <ul>{result.target_users.map((item) => <li key={item}>{item}</li>)}</ul>
                    </div>
                  </div>

                  {/* Differentiators / Next steps */}
                  <div className="columns">
                    <div className="card-list">
                      <h3>Differentiators</h3>
                      <ul>{result.differentiators.map((item) => <li key={item}>{item}</li>)}</ul>
                    </div>
                    <div className="card-list experiments-card">
                      <h3>Next steps</h3>
                      <ul>{result.next_steps.map((item) => <li key={item}>{item}</li>)}</ul>
                    </div>
                  </div>

                  {/* Architecture — FROM API RESULT */}
                  <div className="architecture-card">
                    <div className="section-bar">
                      <h3>How the system is built</h3>
                    </div>
                    {architectureBlocks.length > 0 ? (
                      <div className="architecture-grid">
                        {architectureBlocks.map((block) => (
                          <article className="architecture-node" key={block.title}>
                            <strong>{block.title}</strong>
                            <p>{block.detail}</p>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="empty">No architecture blocks returned.</p>
                    )}
                  </div>

                  {/* Tech stack */}
                  <div className="stack-card">
                    <div className="section-bar">
                      <h3>Core stack in this project</h3>
                    </div>
                    <div className="stack-grid">
                      {result.tech_stack.map((item) => (
                        <span className="stack-chip" key={item}>{item}</span>
                      ))}
                    </div>
                  </div>

                  {/* Roadmap — FROM API RESULT */}
                  <div className="roadmap-card">
                    <div className="section-bar">
                      <h3>Proper roadmap for this project summary</h3>
                    </div>
                    {roadmap.length > 0 ? (
                      <div className="roadmap-grid">
                        {roadmap.map((phase, index) => (
                          <article className="roadmap-phase" key={phase.title}>
                            <h4>
                              <span className="phase-number">0{index + 1}</span>
                              {phase.title}
                            </h4>
                            <ul>
                              {phase.tasks.map((task) => (
                                <li key={task}>{task}</li>
                              ))}
                            </ul>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="empty">No roadmap returned from the backend.</p>
                    )}
                  </div>
                </div>
              )}
            </section>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;