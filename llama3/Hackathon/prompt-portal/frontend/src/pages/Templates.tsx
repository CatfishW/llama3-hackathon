import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, templatesAPI } from '../api'
import { useIsMobile } from '../hooks/useIsMobile'
import { useTemplates } from '../contexts/TemplateContext'
import { useTutorial } from '../contexts/TutorialContext'

type Template = {
  id: number
  title: string
  description?: string
  content: string
  is_active: boolean
  version: number
  created_at: string
  updated_at: string
  user_id: number
}

export default function Templates() {
  const isMobile = useIsMobile()
  const { templates: items, loading, refreshTemplates, removeTemplate } = useTemplates()
  const [err, setErr] = useState<string | null>(null)
  const { runTutorial } = useTutorial()

  useEffect(() => {
    const hasSeenTemplatesTutorial = localStorage.getItem('tutorial_seen_templates')
    if (!hasSeenTemplatesTutorial && !loading) {
      runTutorial([
        { target: '#new-template-btn', title: 'Start Creating', content: 'Ready to build something awesome? Click here to create your first prompt template.', position: 'left' },
        { target: '#design-criteria-panel', title: 'Best Practices', content: 'Not sure what makes a good prompt? We\'ve compiled a list of design criteria to help you out.', position: 'bottom' },
        { target: '#criteria-toggle-btn', title: 'Toggle Visibility', content: 'Minimize this panel to clear up your workspace once you are familiar with the concepts.', position: 'bottom' },
        { target: '#quantified-metrics-panel', title: 'Measure Performance', content: 'Use these concrete metrics and formulas to scientifically evaluate your agent\'s performance.', position: 'bottom' },
        { target: '#metrics-toggle-btn', title: 'Metric Details', content: 'Click here to expand or collapse the comprehensive metric definitions.', position: 'bottom' },
        { target: '#template-list-container', title: 'Your Repository', content: 'All your saved templates are listed here. You can view, edit, or delete them anytime.', position: 'top' },
      ]);
      localStorage.setItem('tutorial_seen_templates', 'true');
    }
  }, [loading, runTutorial]);
  // Criteria panel toggle
  const [showCriteria, setShowCriteria] = useState(() => !window.matchMedia || window.innerWidth > 900) // hide large panels by default on mobile
  // Metrics panel toggle
  const [showMetrics, setShowMetrics] = useState(() => !window.matchMedia || window.innerWidth > 900)
  // Track which metric nodes are expanded
  const [openMetrics, setOpenMetrics] = useState<Set<number>>(new Set())
  const toggleMetric = (i: number) => {
    setOpenMetrics(prev => {
      const next = new Set(prev)
      next.has(i) ? next.delete(i) : next.add(i)
      return next
    })
  }

  // Curated criteria list for good LAM prompt templates (beyond end score)
  const criteria: Array<{ title: string; desc: string; icon: string; accent: string }> = [
    {
      title: 'Clarity & Specificity',
      desc: 'State goals, allowed actions, constraints, success conditions. Minimize ambiguity and conflicting rules.',
      icon: 'fa-bullseye',
      accent: 'linear-gradient(45deg, #6a11cb, #2575fc)'
    },
    {
      title: 'Actionability & Structure',
      desc: 'Enforce a tight Perceive → Plan → Act loop, short deterministic actions, and explicit decision steps.',
      icon: 'fa-sitemap',
      accent: 'linear-gradient(45deg, #ff9966, #ff5e62)'
    },
    {
      title: 'Path Efficiency',
      desc: 'Encourage shortest paths, minimal backtracking, and dead-end avoidance (track path-length ratio and backtrack %).',
      icon: 'fa-route',
      accent: 'linear-gradient(45deg, #00b09b, #96c93d)'
    },
    {
      title: 'Safety & Recovery',
      desc: 'Guardrails for collisions/stuck states with recovery playbooks and timeouts.',
      icon: 'fa-shield-halved',
      accent: 'linear-gradient(45deg, #f7971e, #ffd200)'
    },
    {
      title: 'Consistency',
      desc: 'Stable behavior across seeds/mazes; low variance in success and steps-to-goal.',
      icon: 'fa-stream',
      accent: 'linear-gradient(45deg, #36d1dc, #5b86e5)'
    },
    {
      title: 'Observability',
      desc: 'Require concise step logs and rationale to enable debugging and replay.',
      icon: 'fa-eye',
      accent: 'linear-gradient(45deg, #11998e, #38ef7d)'
    },
    {
      title: 'Robustness',
      desc: 'Handle noisy or unexpected observations with explicit fallbacks and if-else branches.',
      icon: 'fa-hat-wizard',
      accent: 'linear-gradient(45deg, #ee0979, #ff6a00)'
    },
    {
      title: 'Controllability',
      desc: 'Expose tunable knobs like {risk_tolerance} and {explore_rate} to adapt behavior without rewrites.',
      icon: 'fa-sliders',
      accent: 'linear-gradient(45deg, #614385, #516395)'
    },
    {
      title: 'Token & Latency Efficiency',
      desc: 'Be concise; constrain output format and token budget per step to keep costs and latency low.',
      icon: 'fa-feather',
      accent: 'linear-gradient(45deg, #12c2e9, #c471ed)'
    },
    {
      title: 'Mechanics Alignment',
      desc: 'Map instructions to valid game actions; forbid unsupported commands and clarify no-ops.',
      icon: 'fa-gamepad',
      accent: 'linear-gradient(45deg, #f953c6, #b91d73)'
    },
    {
      title: 'Evaluation Hooks',
      desc: 'Define telemetry fields (steps, backtracks, dead-ends, collisions) and explicit success criteria.',
      icon: 'fa-clipboard-check',
      accent: 'linear-gradient(45deg, #43cea2, #185a9d)'
    }
  ]

  // Quantified metrics and formulas to assess prompt templates (with details)
  const metrics: Array<{
    name: string
    formula: string
    good: string
    bad: string
    icon: string
    tip?: string
    details: {
      what: string
      how: string
      improve: string[]
      pitfalls: string[]
      example?: string
    }
  }> = [
      {
        name: 'Success Rate (SR)',
        formula: 'SR = (1/N) · ∑ 𝟙[episode i reached goal]',
        good: '≥ 85% (across ≥20 seeds)',
        bad: '< 60%',
        icon: 'fa-star',
        tip: 'Average across diverse mazes/seeds.',
        details: {
          what: 'Share of episodes where the agent reaches the goal under a template.',
          how: 'Run N episodes, count successes, divide by N. Report mean ± std across randomized seeds.',
          improve: [
            'Tighten goal definition and stop condition.',
            'Clarify invalid actions and recovery paths.',
            'Add explicit heuristics for dead-ends and loops.'
          ],
          pitfalls: [
            'Small N inflates SR; use ≥20 seeds.',
            'Overfitting to a single maze layout.'
          ],
          example: 'If 18 of 20 runs succeed: SR = 18/20 = 0.90'
        }
      },
      {
        name: 'Path Efficiency (PE)',
        formula: 'PE = optimal_steps / actual_steps',
        good: '≥ 0.85',
        bad: '< 0.60',
        icon: 'fa-route',
        tip: 'Closer to 1.0 means near-optimal paths.',
        details: {
          what: 'How close the agent’s path length is to the shortest known path.',
          how: 'Compute optimal shortest path length (BFS on grid). Divide by agent steps to goal.',
          improve: [
            'Bias to forward progress (avoid revisits).',
            'Penalize cycles and repeated cells.',
            'Use “lookahead” prompts before committing to a long move.'
          ],
          pitfalls: [
            'Unknown optimal path approximation can skew PE.',
            'Counting thinking steps instead of movement steps.'
          ],
          example: 'Optimal=30, Actual=36 → PE = 30/36 = 0.83'
        }
      },
      {
        name: 'Backtrack Ratio (BR)',
        formula: 'BR = backtrack_steps / total_steps',
        good: '≤ 10%',
        bad: '≥ 25%',
        icon: 'fa-arrows-rotate',
        tip: 'High BR signals dithering; tighten planning.',
        details: {
          what: 'Share of steps that undo previous progress (returning to recently visited cells).',
          how: 'Detect moves to an immediately previous cell or within a short visit window and divide by total steps.',
          improve: [
            'Require a Perceive → Plan → Act loop with explicit rationale.',
            'Cache visited states and discourage re-entry without new info.',
            'Add "commit window" to avoid flip-flopping decisions.'
          ],
          pitfalls: [
            'Legitimate detours may be miscounted as backtracks.',
            'Too strict rules can block necessary retreats around obstacles.'
          ],
          example: 'If 12 of 140 steps were backtracks → BR = 12/140 = 8.6%'
        }
      },
      {
        name: 'Collision Rate (CR)',
        formula: 'CR = collisions / total_steps',
        good: '≈ 0',
        bad: '≥ 5%',
        icon: 'fa-circle-xmark',
        tip: 'Use guardrails and recovery playbooks.',
        details: {
          what: 'Frequency of invalid moves into walls/obstacles.',
          how: 'Count invalid action attempts (engine rejects) over total steps.',
          improve: [
            'Validate actions against observed map before output.',
            'Add preflight checks: “If wall ahead, choose alternate”.',
            'Provide a fallback recovery macro after a collision.'
          ],
          pitfalls: [
            'Loose parsing of model outputs can send unintended actions.',
            'Ambiguous observation descriptions increase errors.'
          ]
        }
      },
      {
        name: 'Dead-end Entries (DE)',
        formula: 'DE = dead_end_entries / total_steps',
        good: '≤ 2%',
        bad: '≥ 10%',
        icon: 'fa-ban',
        tip: 'Improve local lookahead and pruning.',
        details: {
          what: 'How often the agent enters cul-de-sacs requiring backtracking.',
          how: 'Mark dead-end cells via local topology or post-hoc trace; divide entries by total steps.',
          improve: [
            'Use micro-planning to evaluate branches before entering.',
            'Prefer unexplored paths with higher exit potential.',
            'Add rule: avoid depth-1 branches unless necessary.'
          ],
          pitfalls: [
            'Incorrect dead-end labeling skews metric.'
          ]
        }
      },
      {
        name: 'Steps Variability (σ)',
        formula: 'σ = sqrt((1/N) · ∑(s_i − s̄)^2)',
        good: 'Low (stable across seeds)',
        bad: 'High (erratic)',
        icon: 'fa-chart-line',
        tip: 'Lower variance → more consistent behavior.',
        details: {
          what: 'Standard deviation of steps-to-goal across seeds.',
          how: 'Record steps for each successful episode; compute standard deviation.',
          improve: [
            'Reduce randomness in exploration steps.',
            'Strengthen deterministic tie-breaking in choices.'
          ],
          pitfalls: [
            'Mixing failures with successes in σ calculation.'
          ]
        }
      },
      {
        name: 'Latency per Step (L)',
        formula: 'L = mean(response_time_ms_per_action)',
        good: '≤ 400 ms',
        bad: '≥ 1000 ms',
        icon: 'fa-hourglass-half',
        tip: 'Constrain output and context to reduce thinking time.',
        details: {
          what: 'Average model response time to produce an action.',
          how: 'Measure time from observation to first valid action token; average over steps.',
          improve: [
            'Reduce prompt verbosity; remove non-essential context.',
            'Use compact output schemas with few tokens.',
            'Cache static instructions; stream only deltas.'
          ],
          pitfalls: [
            'Network latency interfering with measurement.'
          ]
        }
      },
      {
        name: 'Tokens per Decision (TPD)',
        formula: 'TPD = output_tokens_per_action',
        good: '≤ 80',
        bad: '≥ 200',
        icon: 'fa-feather',
        tip: 'Use strict formats and concise rationales.',
        details: {
          what: 'Average number of output tokens generated per action.',
          how: 'Count tokens in the model’s action message. Mean over steps.',
          improve: [
            'Replace prose with structured JSON or terse commands.',
            'Make rationale optional or bounded in length.',
            'Enforce a maximum token budget per step.'
          ],
          pitfalls: [
            'Verbose logging mingled with the action payload.'
          ]
        }
      },
      {
        name: 'Action Validity (AV)',
        formula: 'AV = valid_actions / total_actions',
        good: '≈ 100%',
        bad: '≤ 95%',
        icon: 'fa-list-check',
        tip: 'Disallow unsupported commands and no-ops.',
        details: {
          what: 'Share of outputs that parse and map to allowed game actions.',
          how: 'Validate each action against schema and game mechanics; divide valid by total.',
          improve: [
            'Schema-lock outputs with enums for actions.',
            'Reject/reprompt on invalid format with a brief reminder.'
          ],
          pitfalls: [
            'Silent coercion of malformed outputs hides errors.'
          ]
        }
      },
      {
        name: 'Format Compliance (FC)',
        formula: 'FC = parse_success / total_responses',
        good: '≥ 99%',
        bad: '≤ 95%',
        icon: 'fa-code',
        tip: 'Schema-locked outputs avoid parse errors.',
        details: {
          what: 'How often the model returns exactly the expected schema.',
          how: 'Attempt to parse each response; count successes over total.',
          improve: [
            'Provide a minimal example of valid output.',
            'Use explicit JSON schema and forbidden fields list.'
          ],
          pitfalls: [
            'Permissive parser hides non-compliance.'
          ]
        }
      },
      {
        name: 'Recovery Time (RT)',
        formula: 'RT = mean(steps_to_recover_from_stuck)',
        good: '≤ 3 steps',
        bad: '≥ 8 steps',
        icon: 'fa-life-ring',
        tip: 'Have explicit stuck detection and recovery macro.',
        details: {
          what: 'Average steps needed to resume progress after stuck/collision.',
          how: 'Detect stuck state (no progress for K steps); count steps until forward progress.',
          improve: [
            'Add a recovery subroutine with clear triggers.',
            'Reset local memory of visited nodes after recovery.'
          ],
          pitfalls: [
            'Vague stuck criteria cause noisy RT.'
          ]
        }
      },
      {
        name: 'Robustness Pass Rate (RPR)',
        formula: 'RPR = passes_under_noise / trials',
        good: '≥ 80%',
        bad: '≤ 50%',
        icon: 'fa-shield-halved',
        tip: 'Test with perturbed observations and random seeds.',
        details: {
          what: 'How often the agent maintains success under noise/perturbations.',
          how: 'Add observation noise or randomize layouts; count passes over trials.',
          improve: [
            'Write fallback branches for partial observability.',
            'Discourage reliance on spurious text cues.'
          ],
          pitfalls: [
            'Testing with unrealistic noise distributions.'
          ]
        }
      }
    ]

  async function remove(id: number, title: string) {
    if (!confirm(`Delete template "${title}"? This action cannot be undone.`)) return
    try {
      await templatesAPI.deleteTemplate(id)
      removeTemplate(id)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to delete template')
    }
  }

  const containerStyle = {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: isMobile ? '24px 12px 56px' : '40px 20px'
  }

  const headerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: isMobile ? '28px' : '40px',
    flexWrap: 'wrap' as const,
    gap: '20px'
  }

  const cardStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '15px',
    padding: '25px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    marginBottom: '20px',
    transition: 'all 0.3s ease'
  }

  // Styles shared by guidance panels
  const criteriaHeaderStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px'
  }

  const criteriaGridStyle = {
    display: 'grid',
    gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: isMobile ? '12px' : '16px'
  }

  const pillStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '6px 12px',
    borderRadius: 999,
    color: 'white',
    background: 'rgba(255,255,255,0.1)',
    border: '1px solid rgba(255,255,255,0.2)',
    fontSize: '0.9rem'
  }

  const buttonStyle = {
    background: 'linear-gradient(45deg, #4ecdc4, #44a08d)',
    color: 'white',
    padding: '12px 24px',
    borderRadius: '25px',
    textDecoration: 'none',
    fontSize: '1rem',
    fontWeight: '600',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'all 0.3s ease',
    border: 'none',
    cursor: 'pointer'
  }

  const actionButtonStyle = {
    padding: '8px 16px',
    borderRadius: '20px',
    fontSize: '0.9rem',
    fontWeight: '500',
    textDecoration: 'none',
    transition: 'all 0.3s ease',
    border: 'none',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px'
  }

  const editButtonStyle = {
    ...actionButtonStyle,
    background: 'rgba(78, 205, 196, 0.3)',
    color: '#4ecdc4',
    border: '1px solid rgba(78, 205, 196, 0.5)'
  }

  const deleteButtonStyle = {
    ...actionButtonStyle,
    background: 'rgba(255, 107, 107, 0.3)',
    color: '#ff6b6b',
    border: '1px solid rgba(255, 107, 107, 0.5)'
  }

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <div>
          <h1 style={{ fontSize: isMobile ? '2rem' : '2.5rem', fontWeight: '700', marginBottom: '10px', lineHeight: 1.2 }}>
            <i className="fas fa-file-code" style={{ marginRight: '15px' }}></i>
            My Templates
          </h1>
          <p style={{ opacity: '0.8', fontSize: isMobile ? '1rem' : '1.1rem' }}>
            Manage your prompt templates for the LAM Maze Game
          </p>
        </div>
        <Link
          id="new-template-btn"
          to="/templates/new"
          style={buttonStyle}
          onMouseOver={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)'
            e.currentTarget.style.boxShadow = '0 4px 15px rgba(78, 205, 196, 0.4)'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = 'none'
          }}
        >
          <i className="fas fa-plus"></i>
          New Template
        </Link>
      </div>

      {/* Criteria Panel: displayed under Templates navbar/header */}
      <div id="design-criteria-panel" style={{ ...cardStyle, border: '1px solid rgba(255,255,255,0.25)' }}
        onMouseOver={(e) => {
          ; (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 25px rgba(0,0,0,0.15)'
            ; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)'
        }}
        onMouseOut={(e) => {
          ; (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'
            ; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'
        }}
      >
        <div style={criteriaHeaderStyle}>
          <div>
            <div style={pillStyle}>
              <i className="fas fa-lightbulb"></i>
              Design Criteria
            </div>
            <h2 style={{ margin: '10px 0 4px', fontSize: isMobile ? '1.3rem' : '1.6rem', fontWeight: 700, lineHeight: 1.25 }}>
              What makes a good LAM prompt template (beyond final score)
            </h2>
            <p style={{ opacity: 0.8, margin: 0 }}>
              Use these principles to craft prompts that are efficient, controllable, and robust.
            </p>
          </div>
          <button
            id="criteria-toggle-btn"
            onClick={() => setShowCriteria(v => !v)}
            style={{
              ...actionButtonStyle,
              background: 'rgba(255,255,255,0.08)',
              color: 'white',
              border: '1px solid rgba(255,255,255,0.25)'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.15)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.08)'
            }}
            title={showCriteria ? 'Hide criteria' : 'Show criteria'}
          >
            <i className={`fas ${showCriteria ? 'fa-chevron-up' : 'fa-chevron-down'}`}></i>
            {showCriteria ? 'Hide' : 'Show'}
          </button>
        </div>

        {showCriteria && (
          <div style={criteriaGridStyle}>
            {criteria.map((c, idx) => (
              <div
                key={idx}
                style={{
                  borderRadius: 12,
                  padding: 16,
                  background: 'rgba(0,0,0,0.35)',
                  border: '1px solid rgba(255,255,255,0.12)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 10,
                      background: c.accent,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'white',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.25)'
                    }}
                  >
                    <i className={`fas ${c.icon}`}></i>
                  </div>
                  <div style={{ fontWeight: 700 }}>{c.title}</div>
                </div>
                <div style={{ opacity: 0.85, lineHeight: 1.5, fontSize: '0.95rem' }}>{c.desc}</div>
              </div>
            ))}
          </div>
        )}

        {/* Quick metric suggestions bar */}
        {showCriteria && (
          <div style={{ marginTop: 16, display: 'flex', flexWrap: 'wrap', gap: 8, opacity: 0.9 }}>
            {[
              'Path efficiency = optimal/actual',
              'Backtrack ratio < 10%',
              'Collisions = 0',
              'Tokens/decision budget',
              'Latency per step budget',
              'Variance in steps ↓'
            ].map((t, i) => (
              <span key={i} style={{ ...pillStyle, background: 'rgba(255,255,255,0.08)' }}>
                <i className="fas fa-check"></i>
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Quantified Metrics Panel: concrete formulas and thresholds */}
      <div id="quantified-metrics-panel" style={{ ...cardStyle, border: '1px solid rgba(255,255,255,0.25)' }}
        onMouseOver={(e) => {
          ; (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 25px rgba(0,0,0,0.15)'
            ; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)'
        }}
        onMouseOut={(e) => {
          ; (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'
            ; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'
        }}
      >
        <div style={criteriaHeaderStyle}>
          <div>
            <div style={pillStyle}>
              <i className="fas fa-calculator"></i>
              Quantified Metrics & Formulas
            </div>
            <h2 style={{ margin: '10px 0 4px', fontSize: isMobile ? '1.3rem' : '1.6rem', fontWeight: 700, lineHeight: 1.25 }}>
              Measure template quality beyond end score
            </h2>
            <p style={{ opacity: 0.8, margin: 0 }}>
              Evaluate across multiple episodes (e.g., N = 20 seeds). Aim for green targets and avoid red thresholds.
            </p>
          </div>
          <button
            id="metrics-toggle-btn"
            onClick={() => setShowMetrics(v => !v)}
            style={{
              ...actionButtonStyle,
              background: 'rgba(255,255,255,0.08)',
              color: 'white',
              border: '1px solid rgba(255,255,255,0.25)'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.15)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.08)'
            }}
            title={showMetrics ? 'Hide metrics' : 'Show metrics'}
          >
            <i className={`fas ${showMetrics ? 'fa-chevron-up' : 'fa-chevron-down'}`}></i>
            {showMetrics ? 'Hide' : 'Show'}
          </button>
        </div>

        {showMetrics && (
          <div style={criteriaGridStyle}>
            {metrics.map((m, idx) => (
              <div
                key={idx}
                style={{
                  borderRadius: 12,
                  padding: 16,
                  background: 'rgba(0,0,0,0.35)',
                  border: '1px solid rgba(255,255,255,0.12)'
                }}
              >
                <div
                  role="button"
                  tabIndex={0}
                  aria-expanded={openMetrics.has(idx)}
                  onClick={() => toggleMetric(idx)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleMetric(idx) } }}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, cursor: 'pointer' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 10,
                        background: 'linear-gradient(45deg, #4ecdc4, #44a08d)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'white',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.25)'
                      }}
                    >
                      <i className={`fas ${m.icon}`}></i>
                    </div>
                    <div>
                      <div style={{ fontWeight: 700 }}>{m.name}</div>
                      <div style={{ fontFamily: 'Monaco, Consolas, monospace', fontSize: '0.9rem', opacity: 0.95 }}>{m.formula}</div>
                    </div>
                  </div>
                  <i className={`fas ${openMetrics.has(idx) ? 'fa-chevron-up' : 'fa-chevron-down'}`} style={{ opacity: 0.8 }}></i>
                </div>

                <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderRadius: 999, background: 'rgba(46, 204, 113, 0.2)', border: '1px solid rgba(46, 204, 113, 0.5)', color: '#2ecc71' }}>
                    <i className="fas fa-thumbs-up"></i>
                    Good: {m.good}
                  </span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderRadius: 999, background: 'rgba(255, 107, 107, 0.2)', border: '1px solid rgba(255, 107, 107, 0.5)', color: '#ff6b6b' }}>
                    <i className="fas fa-thumbs-down"></i>
                    Bad: {m.bad}
                  </span>
                </div>

                {m.tip && (
                  <div style={{ opacity: 0.75, marginTop: 8, fontSize: '0.9rem' }}>
                    <i className="fas fa-lightbulb"></i> {m.tip}
                  </div>
                )}

                {openMetrics.has(idx) && (
                  <div style={{ marginTop: 12, background: 'rgba(255,255,255,0.06)', borderRadius: 10, padding: 12, border: '1px solid rgba(255,255,255,0.12)' }}>
                    <div style={{ marginBottom: 8 }}>
                      <strong>What it is:</strong>
                      <div style={{ opacity: 0.9 }}>{m.details.what}</div>
                    </div>
                    <div style={{ marginBottom: 8 }}>
                      <strong>How to compute:</strong>
                      <div style={{ opacity: 0.9 }}>{m.details.how}</div>
                    </div>
                    {m.details.example && (
                      <div style={{ marginBottom: 8 }}>
                        <strong>Example:</strong>
                        <div style={{ opacity: 0.9, fontFamily: 'Monaco, Consolas, monospace' }}>{m.details.example}</div>
                      </div>
                    )}
                    <div style={{ marginBottom: 8 }}>
                      <strong>Improve:</strong>
                      <ul style={{ margin: '6px 0 0 18px' }}>
                        {m.details.improve.map((it, i) => (<li key={i} style={{ marginBottom: 4, opacity: 0.9 }}>{it}</li>))}
                      </ul>
                    </div>
                    <div>
                      <strong>Pitfalls:</strong>
                      <ul style={{ margin: '6px 0 0 18px' }}>
                        {m.details.pitfalls.map((it, i) => (<li key={i} style={{ marginBottom: 4, opacity: 0.9 }}>{it}</li>))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {showMetrics && (
          <div style={{ marginTop: 14, opacity: 0.8, fontSize: '0.9rem' }}>
            Notes: Compute per episode, then report mean ± std over seeds. PE uses shortest known path as optimal. Time and tokens are per action decision.
          </div>
        )}
      </div>

      {err && (
        <div style={{
          background: 'rgba(255, 107, 107, 0.2)',
          border: '1px solid rgba(255, 107, 107, 0.4)',
          borderRadius: '10px',
          padding: '15px',
          marginBottom: '20px',
          color: '#ff6b6b',
          textAlign: 'center'
        }}>
          <i className="fas fa-exclamation-triangle" style={{ marginRight: '8px' }}></i>
          {err}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px' }}>
          <i className="fas fa-spinner fa-spin" style={{ fontSize: '2rem', marginBottom: '20px' }}></i>
          <p style={{ fontSize: '1.1rem', opacity: '0.8' }}>Loading templates...</p>
        </div>
      ) : items.length === 0 ? (
        <div style={{
          ...cardStyle,
          textAlign: 'center',
          padding: '60px 40px'
        }}>
          <i className="fas fa-file-code" style={{ fontSize: '4rem', marginBottom: '20px', opacity: '0.5' }}></i>
          <h3 style={{ fontSize: '1.8rem', marginBottom: '15px', fontWeight: '600' }}>
            No templates yet
          </h3>
          <p style={{ opacity: '0.8', marginBottom: '30px', fontSize: '1.1rem' }}>
            Create your first prompt template to start guiding AI agents through mazes!
          </p>
          <Link
            to="/templates/new"
            style={buttonStyle}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 4px 15px rgba(78, 205, 196, 0.4)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            <i className="fas fa-plus"></i>
            Create Your First Template
          </Link>
        </div>
      ) : (
        <div id="template-list-container">
          {items.map(template => (
            <div
              key={template.id}
              style={cardStyle}
              onMouseOver={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 8px 25px rgba(0,0,0,0.15)'
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '15px',
                flexWrap: 'wrap',
                gap: '15px'
              }}>
                <div style={{ flex: 1, minWidth: '250px' }}>
                  <h3 style={{
                    fontSize: '1.4rem',
                    fontWeight: '600',
                    marginBottom: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                  }}>
                    {template.title}
                    {template.is_active && (
                      <span style={{
                        background: 'rgba(76, 175, 80, 0.3)',
                        color: '#4caf50',
                        padding: '4px 12px',
                        borderRadius: '12px',
                        fontSize: '0.8rem',
                        fontWeight: '500',
                        border: '1px solid rgba(76, 175, 80, 0.5)'
                      }}>
                        <i className="fas fa-check-circle" style={{ marginRight: '4px' }}></i>
                        Active
                      </span>
                    )}
                  </h3>

                  {template.description && (
                    <p style={{
                      opacity: '0.8',
                      fontSize: '1rem',
                      lineHeight: '1.5',
                      marginBottom: '10px'
                    }}>
                      {template.description}
                    </p>
                  )}

                  <div style={{
                    display: 'flex',
                    gap: '15px',
                    fontSize: '0.9rem',
                    opacity: '0.7',
                    flexWrap: 'wrap'
                  }}>
                    <span>
                      <i className="fas fa-code-branch" style={{ marginRight: '5px' }}></i>
                      Version {template.version}
                    </span>
                    <span>
                      <i className="fas fa-calendar" style={{ marginRight: '5px' }}></i>
                      {new Date(template.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                <div style={{
                  display: 'flex',
                  gap: '10px',
                  alignItems: 'center'
                }}>
                  <Link
                    to={`/templates/${template.id}`}
                    style={editButtonStyle}
                    onMouseOver={(e) => {
                      e.currentTarget.style.background = 'rgba(78, 205, 196, 0.5)'
                      e.currentTarget.style.transform = 'translateY(-1px)'
                    }}
                    onMouseOut={(e) => {
                      e.currentTarget.style.background = 'rgba(78, 205, 196, 0.3)'
                      e.currentTarget.style.transform = 'translateY(0)'
                    }}
                  >
                    <i className="fas fa-edit"></i>
                    Edit
                  </Link>

                  <button
                    onClick={() => remove(template.id, template.title)}
                    style={deleteButtonStyle}
                    onMouseOver={(e) => {
                      e.currentTarget.style.background = 'rgba(255, 107, 107, 0.5)'
                      e.currentTarget.style.transform = 'translateY(-1px)'
                    }}
                    onMouseOut={(e) => {
                      e.currentTarget.style.background = 'rgba(255, 107, 107, 0.3)'
                      e.currentTarget.style.transform = 'translateY(0)'
                    }}
                  >
                    <i className="fas fa-trash"></i>
                    Delete
                  </button>
                </div>
              </div>

              <div style={{
                background: 'rgba(0, 0, 0, 0.3)',
                borderRadius: '8px',
                padding: '15px',
                fontFamily: 'Monaco, Consolas, monospace',
                fontSize: '0.9rem',
                lineHeight: '1.4',
                overflow: 'auto',
                maxHeight: '200px',
                border: '1px solid rgba(255, 255, 255, 0.1)'
              }}>
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  margin: 0,
                  color: 'rgba(255, 255, 255, 0.9)'
                }}>
                  {template.content}
                </pre>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
