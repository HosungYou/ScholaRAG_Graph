'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  Network,
  Sparkles,
  Brain,
  Target,
  Calendar,
  GitBranch,
  Workflow,
  FileText,
  Layers,
} from 'lucide-react';
import { Header, Footer } from '@/components/layout';
import { ThemeToggle } from '@/components/ui';
import {
  HeroBackground,
  ScrollReveal,
  FloatingBadges,
  CosmicStarfield,
  LiveStats,
  ViewModePreview,
} from '@/components/home';

/* ============================================================
   ScholaRAG Graph - Cosmic Landing Page
   Deep Nebula Theme: #050510 base + cyan/purple/pink nebula

   Sections:
   1. Full-screen constellation hero
   2. Live stats counter (animated count-up)
   3. Quick action cards
   4. Feature showcase (v0.12–v0.13)
   5. 6-Agent pipeline visualization
   6. View mode preview (6 tabs)
   7. Cosmic CTA
   ============================================================ */

const features = [
  {
    title: 'AI Topic Clustering',
    description:
      'LLM-powered cluster labeling with concept grouping, keyword extraction, and inter-cluster relationship mapping.',
    icon: <Layers className="w-6 h-6" />,
    color: '#a78bfa',
    version: 'v0.12.0',
  },
  {
    title: 'Gap Analysis',
    description:
      'Structural gap detection between concept clusters with AI-generated research questions and paper recommendations.',
    icon: <Target className="w-6 h-6" />,
    color: '#f472b6',
    version: 'v0.12.0',
  },
  {
    title: 'Temporal View',
    description:
      'Time-axis visualization showing concept emergence by publication year with D3.js charts and cumulative growth.',
    icon: <Calendar className="w-6 h-6" />,
    color: '#fbbf24',
    version: 'v0.12.1',
  },
  {
    title: 'Citation Network',
    description:
      'Litmaps-style paper citation scatter plot built on-demand from Semantic Scholar, showing citation relationships.',
    icon: <GitBranch className="w-6 h-6" />,
    color: '#34d399',
    version: 'v0.13.0',
  },
  {
    title: 'Concept Flow',
    description:
      'Traces how concepts propagate through citation chains, revealing which ideas influenced research directions.',
    icon: <Workflow className="w-6 h-6" />,
    color: '#c084fc',
    version: 'v0.13.1',
  },
  {
    title: '6-Agent Pipeline',
    description:
      'Intent, Concept Extraction, Task Planning, Query Execution, Chain-of-Thought, and Response Generation.',
    icon: <Brain className="w-6 h-6" />,
    color: '#22d3ee',
    version: 'Core',
  },
];

const pipelineSteps = [
  { step: '1', label: 'Intent', color: '#22d3ee' },
  { step: '2', label: 'Extraction', color: '#a78bfa' },
  { step: '3', label: 'Planning', color: '#c084fc' },
  { step: '4', label: 'Query', color: '#818cf8' },
  { step: '5', label: 'Reasoning', color: '#f472b6' },
  { step: '6', label: 'Response', color: '#34d399' },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#050510] text-white flex flex-col relative">
      {/* Full cosmic starfield + nebula background */}
      <CosmicStarfield />

      {/* Skip Link */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <Header rightContent={<ThemeToggle variant="dropdown" />} />

      <main id="main-content" className="flex-1 relative" style={{ zIndex: 1 }}>
        {/* ─── Hero Section: Full-Screen Constellation ─── */}
        <section className="relative min-h-[85vh] flex items-center overflow-hidden">
          {/* Constellation graph background */}
          <div className="absolute inset-0">
            <HeroBackground />
          </div>

          {/* Floating Tech Badges */}
          <FloatingBadges />

          {/* Hero content overlay */}
          <div className="max-w-6xl mx-auto px-6 py-20 relative z-10">
            <div className="max-w-2xl">
              <motion.div
                className="space-y-6"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: [0.25, 0.4, 0.25, 1] }}
              >
                <span className="inline-flex items-center gap-2 text-cyan-400 font-mono text-sm tracking-widest uppercase">
                  <span className="w-8 h-px bg-cyan-400" />
                  Knowledge Graph Platform
                </span>
                <h1 className="font-display text-5xl md:text-6xl lg:text-7xl text-white leading-[1.05]">
                  Transform Research
                  <br />
                  into{' '}
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400">
                    Connected
                  </span>
                  <br />
                  <span className="italic text-white/90">Insights</span>
                </h1>
              </motion.div>

              <motion.p
                className="text-white/50 text-lg max-w-lg leading-relaxed mt-6"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.15 }}
              >
                A concept-centric knowledge graph platform for systematic literature review.
                Watch your papers transform into interconnected knowledge —{' '}
                <span className="text-white/80">in real-time</span>.
              </motion.p>

              {/* CTA Buttons */}
              <motion.div
                className="flex flex-wrap gap-4 mt-8"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.3 }}
              >
                <Link
                  href="/import"
                  className="group inline-flex items-center gap-2 px-7 py-3.5 rounded-md font-medium text-[#050510] bg-gradient-to-r from-cyan-400 to-cyan-300 hover:from-cyan-300 hover:to-cyan-200 transition-all duration-300 shadow-[0_0_30px_rgba(34,211,238,0.3)]"
                >
                  <span>Start Importing</span>
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </Link>
                <Link
                  href="/projects"
                  className="inline-flex items-center gap-2 px-7 py-3.5 rounded-md font-medium text-white/70 border border-white/10 hover:border-white/25 hover:text-white transition-all duration-300 backdrop-blur-sm"
                >
                  View Projects
                </Link>
              </motion.div>
            </div>
          </div>

          {/* Bottom gradient fade */}
          <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#050510] to-transparent pointer-events-none" />
        </section>

        {/* ─── Live Stats Counter ─── */}
        <section className="py-16 relative">
          <ScrollReveal>
            <LiveStats />
          </ScrollReveal>
        </section>

        {/* ─── Quick Actions ─── */}
        <section className="py-10 relative">
          <div className="max-w-6xl mx-auto px-6">
            <div className="grid md:grid-cols-3 gap-5">
              {[
                {
                  href: '/import',
                  icon: <FileText className="w-6 h-6" />,
                  title: 'Import ScholaRAG',
                  desc: 'Build knowledge graph from existing projects',
                  color: '#22d3ee',
                },
                {
                  href: '/projects',
                  icon: <Network className="w-6 h-6" />,
                  title: 'Explore Graphs',
                  desc: 'Interactive visualization with React Flow',
                  color: '#a78bfa',
                },
                {
                  href: '/projects',
                  icon: <Sparkles className="w-6 h-6" />,
                  title: 'Chat with AI',
                  desc: 'Graph-grounded responses with citations',
                  color: '#f472b6',
                },
              ].map((action, i) => (
                <ScrollReveal key={action.title} delay={i * 0.1} direction="up">
                  <Link href={action.href} className="group block">
                    <div
                      className="relative p-6 rounded-lg border backdrop-blur-sm transition-all duration-300"
                      style={{
                        borderColor: `${action.color}15`,
                        background: `linear-gradient(135deg, ${action.color}05, transparent)`,
                      }}
                    >
                      <div
                        className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
                        style={{
                          background: `radial-gradient(ellipse at 30% 0%, ${action.color}15, transparent 70%)`,
                        }}
                      />
                      <div className="relative">
                        <div
                          className="mb-4 inline-flex items-center justify-center w-10 h-10 rounded-md border"
                          style={{
                            color: action.color,
                            borderColor: `${action.color}30`,
                            backgroundColor: `${action.color}10`,
                          }}
                        >
                          {action.icon}
                        </div>
                        <h3 className="font-display text-lg text-white mb-1.5 group-hover:text-cyan-300 transition-colors">
                          {action.title}
                        </h3>
                        <p className="text-white/40 text-sm leading-relaxed">{action.desc}</p>
                        <ArrowRight
                          className="w-4 h-4 mt-3 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all"
                          style={{ color: action.color }}
                        />
                      </div>
                    </div>
                  </Link>
                </ScrollReveal>
              ))}
            </div>
          </div>
        </section>

        {/* ─── Feature Showcase (v0.12–v0.13) ─── */}
        <section className="py-20 relative">
          <div className="max-w-6xl mx-auto px-6">
            <ScrollReveal>
              <div className="mb-14 text-center">
                <span className="text-cyan-400 font-mono text-sm tracking-widest uppercase">
                  Capabilities
                </span>
                <h2 className="font-display text-3xl md:text-4xl text-white mt-3">
                  Six Dimensions of Analysis
                </h2>
                <p className="text-white/40 mt-3 max-w-xl mx-auto text-base leading-relaxed">
                  From concept extraction to citation flow — every angle of your research,
                  visualized and connected.
                </p>
              </div>
            </ScrollReveal>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
              {features.map((feature, i) => (
                <ScrollReveal key={feature.title} delay={i * 0.08} direction="up">
                  <div
                    className="group relative p-6 rounded-lg border backdrop-blur-sm h-full transition-all duration-300"
                    style={{
                      borderColor: `${feature.color}15`,
                      background: `linear-gradient(135deg, ${feature.color}05, transparent)`,
                    }}
                  >
                    <div
                      className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
                      style={{
                        background: `radial-gradient(ellipse at 0% 0%, ${feature.color}12, transparent 60%)`,
                      }}
                    />
                    <div className="relative">
                      <div className="flex items-center justify-between mb-4">
                        <div
                          className="inline-flex items-center justify-center w-10 h-10 rounded-md border"
                          style={{
                            color: feature.color,
                            borderColor: `${feature.color}30`,
                            backgroundColor: `${feature.color}10`,
                          }}
                        >
                          {feature.icon}
                        </div>
                        <span
                          className="font-mono text-[10px] px-2 py-0.5 rounded-sm border"
                          style={{
                            color: `${feature.color}90`,
                            borderColor: `${feature.color}20`,
                            backgroundColor: `${feature.color}08`,
                          }}
                        >
                          {feature.version}
                        </span>
                      </div>
                      <h3 className="font-display text-lg text-white mb-2">{feature.title}</h3>
                      <p className="text-white/40 text-sm leading-relaxed">
                        {feature.description}
                      </p>
                    </div>
                  </div>
                </ScrollReveal>
              ))}
            </div>
          </div>
        </section>

        {/* ─── Pipeline Visualization ─── */}
        <section className="py-16 relative">
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background:
                'linear-gradient(180deg, transparent, rgba(34,211,238,0.02) 50%, transparent)',
            }}
          />
          <div className="max-w-6xl mx-auto px-6 relative">
            <ScrollReveal>
              <div className="text-center mb-10">
                <span className="text-purple-400 font-mono text-sm tracking-widest uppercase">
                  How It Works
                </span>
                <h2 className="font-display text-2xl md:text-3xl text-white mt-2">
                  6-Agent Pipeline
                </h2>
              </div>
            </ScrollReveal>

            <div className="flex flex-wrap justify-center gap-3 md:gap-4">
              {pipelineSteps.map((agent, i) => (
                <ScrollReveal key={agent.step} delay={i * 0.08} direction="up">
                  <div className="flex items-center gap-3">
                    <div
                      className="flex items-center gap-2.5 px-4 py-2.5 rounded-md border backdrop-blur-sm"
                      style={{
                        borderColor: `${agent.color}25`,
                        backgroundColor: `${agent.color}08`,
                      }}
                    >
                      <span
                        className="font-mono text-xs font-bold w-5 h-5 flex items-center justify-center rounded-sm"
                        style={{
                          color: agent.color,
                          backgroundColor: `${agent.color}15`,
                        }}
                      >
                        {agent.step}
                      </span>
                      <span className="text-sm font-medium text-white">{agent.label}</span>
                    </div>
                    {i < 5 && (
                      <ArrowRight className="w-3.5 h-3.5 text-white/20 hidden md:block" />
                    )}
                  </div>
                </ScrollReveal>
              ))}
            </div>
          </div>
        </section>

        {/* ─── View Mode Preview ─── */}
        <section className="py-20 relative">
          <ScrollReveal>
            <div className="text-center mb-10">
              <span className="text-pink-400 font-mono text-sm tracking-widest uppercase">
                Visualization Modes
              </span>
              <h2 className="font-display text-3xl md:text-4xl text-white mt-3">
                Six Ways to See Your Research
              </h2>
              <p className="text-white/40 mt-3 max-w-lg mx-auto text-base">
                Each view reveals a different dimension of your knowledge graph.
              </p>
            </div>
          </ScrollReveal>
          <ScrollReveal delay={0.2}>
            <ViewModePreview />
          </ScrollReveal>
        </section>

        {/* ─── CTA Section ─── */}
        <section className="py-20 relative">
          <div className="max-w-6xl mx-auto px-6">
            <ScrollReveal>
              <div
                className="relative rounded-lg overflow-hidden border backdrop-blur-md"
                style={{
                  borderColor: 'rgba(34,211,238,0.15)',
                  background:
                    'linear-gradient(135deg, rgba(34,211,238,0.05), rgba(167,139,250,0.05))',
                }}
              >
                {/* Glow accent */}
                <div
                  className="absolute top-0 left-0 w-full h-px"
                  style={{
                    background:
                      'linear-gradient(90deg, transparent, rgba(34,211,238,0.5), transparent)',
                  }}
                />
                <div className="px-8 py-16 md:py-20 text-center relative">
                  <div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                      background:
                        'radial-gradient(ellipse at 50% 0%, rgba(34,211,238,0.08), transparent 60%), radial-gradient(ellipse at 80% 100%, rgba(167,139,250,0.06), transparent 50%)',
                    }}
                  />
                  <div className="relative">
                    <h2 className="font-display text-3xl md:text-4xl text-white mb-4">
                      Ready to Transform Your Research?
                    </h2>
                    <p className="text-white/40 text-base max-w-lg mx-auto mb-8">
                      Import your ScholaRAG project and start exploring connections you never knew
                      existed.
                    </p>
                    <Link
                      href="/import"
                      className="group inline-flex items-center gap-2 px-8 py-3.5 rounded-md font-medium text-[#050510] bg-gradient-to-r from-cyan-400 to-cyan-300 hover:from-cyan-300 hover:to-cyan-200 transition-all duration-300 shadow-[0_0_30px_rgba(34,211,238,0.3)]"
                    >
                      <span>Get Started</span>
                      <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
                    </Link>
                  </div>
                </div>
              </div>
            </ScrollReveal>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
