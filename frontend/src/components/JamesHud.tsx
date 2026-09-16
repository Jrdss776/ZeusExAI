import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity, BrainCircuit, CalendarDays, Database, MessageSquare, Mic,
  Network, Settings, ShieldCheck,
} from 'lucide-react';
import { useNavigate } from 'react-router';
import { useAppStore } from '../lib/store';

export type JamesHudState = 'IDLE' | 'LISTENING' | 'PROCESSING' | 'SPEAKING';

const STATE_COPY: Record<JamesHudState, string> = {
  IDLE: 'Aguardando comando',
  LISTENING: 'Ouvindo voce',
  PROCESSING: 'Analisando contexto',
  SPEAKING: 'Transmitindo resposta',
};

function useJamesState(): JamesHudState {
  const streamState = useAppStore((s) => s.streamState);
  const [speechState, setSpeechState] = useState('idle');

  useEffect(() => {
    const update = (event: Event) => setSpeechState((event as CustomEvent<string>).detail || 'idle');
    window.addEventListener('james:speech-state', update);
    return () => window.removeEventListener('james:speech-state', update);
  }, []);

  if (speechState === 'recording') return 'LISTENING';
  if (speechState === 'transcribing') return 'PROCESSING';
  if (streamState.isStreaming) return streamState.content ? 'SPEAKING' : 'PROCESSING';
  return 'IDLE';
}

function useHudMotion(ringsRef: React.RefObject<HTMLDivElement | null>, state: JamesHudState) {
  useEffect(() => {
    const root = ringsRef.current;
    if (!root) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0;
    let previous = 0;
    let rotation = 0;
    const speed = state === 'PROCESSING' ? 0.028 : state === 'LISTENING' ? 0.018 : state === 'SPEAKING' ? 0.014 : 0.006;
    const draw = (now: number) => {
      if (document.hidden || reduced.matches) return;
      if (now - previous >= 33) {
        rotation = (rotation + (now - previous) * speed) % 360;
        root.style.setProperty('--hud-rotation', `${rotation}deg`);
        root.style.setProperty('--hud-counter-rotation', `${-rotation * 0.72}deg`);
        previous = now;
      }
      frame = requestAnimationFrame(draw);
    };
    const start = () => {
      cancelAnimationFrame(frame);
      previous = performance.now();
      if (!document.hidden && !reduced.matches) frame = requestAnimationFrame(draw);
    };
    document.addEventListener('visibilitychange', start);
    reduced.addEventListener('change', start);
    start();
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener('visibilitychange', start);
      reduced.removeEventListener('change', start);
    };
  }, [ringsRef, state]);
}

export function JamesHud() {
  const state = useJamesState();
  const ringsRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const selectedModel = useAppStore((s) => s.selectedModel);
  const serverInfo = useAppStore((s) => s.serverInfo);
  const modelLoading = useAppStore((s) => s.modelLoading);
  const deepResearch = useAppStore((s) => s.deepResearch);
  const systemPanelOpen = useAppStore((s) => s.systemPanelOpen);
  const toggleSystemPanel = useAppStore((s) => s.toggleSystemPanel);
  useHudMotion(ringsRef, state);

  const clock = useMemo(() => new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(new Date()), []);
  const coreValue = state === 'IDLE' ? '100' : state === 'LISTENING' ? 'MIC' : state === 'PROCESSING' ? 'AI' : 'TX';
  const coreUnit = state === 'IDLE' ? '%' : 'LIVE';
  const coreStatus = !serverInfo
    ? 'CONECTANDO'
    : state === 'IDLE'
      ? 'AGUARDANDO'
      : state === 'LISTENING'
        ? 'OUVINDO'
        : state === 'PROCESSING'
          ? 'PROCESSANDO'
          : 'RESPONDENDO';

  return (
    <section className="james-hud" data-state={state} aria-label={`James: ${STATE_COPY[state]}`}>
      <div className="james-hud__diagnostics" aria-label="Diagnostico rapido">
        <div className="james-hud__panel-title"><span /> DIAGNOSTICO</div>
        <div className="james-hud__metric"><Network size={13} /><span>NUCLEO</span><strong>{serverInfo ? 'ONLINE' : 'LOCAL'}</strong></div>
        <div className="james-hud__metric"><BrainCircuit size={13} /><span>MODELO</span><strong>{modelLoading ? 'CARREGANDO' : selectedModel || 'AGUARDANDO'}</strong></div>
        <div className="james-hud__metric"><Mic size={13} /><span>VOZ</span><strong>{state === 'LISTENING' ? 'ATIVA' : 'PRONTA'}</strong></div>
        <div className="james-hud__metric"><ShieldCheck size={13} /><span>PRIVACIDADE</span><strong>LOCAL</strong></div>
        <button type="button" onClick={toggleSystemPanel}>{systemPanelOpen ? 'FECHAR TELEMETRIA' : 'ABRIR TELEMETRIA'}</button>
      </div>

      <div className="james-hud__stage">
        <div className="james-hud__coordinates" aria-hidden="true">JX-01 // {clock}</div>
        <div ref={ringsRef} className="james-hud__rings">
          <div className="james-hud__portrait" aria-hidden="true">
            <img src="/identity/james.jpg" alt="" />
          </div>
          <div className="james-hud__ring james-hud__ring--outer" aria-hidden="true" />
          <div className="james-hud__ring james-hud__ring--middle" aria-hidden="true" />
          <div className="james-hud__ring james-hud__ring--inner" aria-hidden="true" />
          <div className="james-hud__crosshair" aria-hidden="true" />
          <button className="james-hud__radial james-hud__radial--chat" onClick={() => navigate('/chat')} title="Chat"><MessageSquare size={14} /><span>Chat</span></button>
          <button className="james-hud__radial james-hud__radial--brain" onClick={() => navigate('/data-sources')} title="Second Brain"><Database size={14} /><span>Brain</span></button>
          <button className="james-hud__radial james-hud__radial--agents" onClick={() => navigate('/commitments')} title="Compromissos"><CalendarDays size={14} /><span>Agenda</span></button>
          <button className="james-hud__radial james-hud__radial--diagnostics" onClick={toggleSystemPanel} title="Diagnostico"><Activity size={14} /><span>Status</span></button>
          <button className="james-hud__radial james-hud__radial--settings" onClick={() => navigate('/settings')} title="Configuracoes"><Settings size={14} /><span>Ajustes</span></button>
          <div className="james-hud__core" aria-hidden="true">
            <div className="james-hud__core-value"><span>{coreValue}</span><small>{coreUnit}</small></div>
            <strong>{coreStatus}</strong>
          </div>
        </div>
        <div className="james-hud__identity">
          <span className="james-hud__eyebrow">ZEUSEXAI // NEURAL INTERFACE</span>
          <h1>JAMES</h1>
          <div className="james-hud__state"><i /> {state} // ONLINE</div>
        </div>
      </div>

      <div className="james-hud__memory">
        <div className="james-hud__panel-title"><span /> SECOND BRAIN</div>
        <Database size={24} />
        <strong>{deepResearch ? 'PESQUISA PROFUNDA ATIVA' : 'MEMORIA CONECTADA'}</strong>
        <p>Fontes, contexto e conhecimento preservados.</p>
        <button type="button" onClick={() => navigate('/data-sources')}>ABRIR FONTES</button>
      </div>
    </section>
  );
}
