import { useCallback, useEffect, useRef, useState } from 'react';
import { AudioLines, MicOff } from 'lucide-react';

type RecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
};

type RecognitionConstructor = new () => RecognitionLike;

function recognitionConstructor(): RecognitionConstructor | null {
  const candidate = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return candidate.SpeechRecognition ?? candidate.webkitSpeechRecognition ?? null;
}

function normalize(text: string) {
  return text
    .toLocaleLowerCase('pt-BR')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();
}

function spokenText(text: string) {
  return text
    .replace(/```[\s\S]*?```/g, ' trecho de código ')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/[*_#>`]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

type Props = {
  paused: boolean;
};

export function JamesVoiceControl({ paused }: Props) {
  const [enabled, setEnabled] = useState(false);
  const [status, setStatus] = useState<'off' | 'listening' | 'speaking' | 'blocked' | 'unsupported'>('off');
  const recognitionRef = useRef<RecognitionLike | null>(null);
  const enabledRef = useRef(false);
  const pausedRef = useRef(paused);
  const busyRef = useRef(false);
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);

  const stopRecognition = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition) return;
    try {
      recognition.stop();
    } catch {
      // Recognition may already be stopped.
    }
  }, []);

  const startRecognition = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition || !enabledRef.current || pausedRef.current || busyRef.current) return;
    try {
      recognition.start();
      setStatus('listening');
    } catch {
      // Browsers throw if recognition is already running.
    }
  }, []);

  const chooseVoice = useCallback(() => {
    const voices = voicesRef.current;
    const ptBR = voices.filter((voice) => /^pt[-_]BR/i.test(voice.lang));
    const maleHint = /antonio|ricardo|felipe|daniel|male|mascul/i;
    return ptBR.find((voice) => maleHint.test(voice.name))
      ?? ptBR[0]
      ?? voices.find((voice) => /^pt/i.test(voice.lang))
      ?? voices[0];
  }, []);

  const speak = useCallback((rawText: string) => {
    if (!('speechSynthesis' in window)) return;
    const text = spokenText(rawText);
    if (!text) return;

    busyRef.current = true;
    stopRecognition();
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'pt-BR';
    utterance.rate = 0.96;
    utterance.pitch = 0.88;
    const voice = chooseVoice();
    if (voice) utterance.voice = voice;

    setStatus('speaking');
    const finish = () => {
      busyRef.current = false;
      if (enabledRef.current) {
        setStatus('listening');
        window.setTimeout(startRecognition, 300);
      } else {
        setStatus('off');
      }
    };
    utterance.onend = finish;
    utterance.onerror = finish;
    window.speechSynthesis.speak(utterance);
  }, [chooseVoice, startRecognition, stopRecognition]);

  useEffect(() => {
    pausedRef.current = paused;
    if (paused) {
      stopRecognition();
    } else if (enabledRef.current && !busyRef.current) {
      window.setTimeout(startRecognition, 250);
    }
  }, [paused, startRecognition, stopRecognition]);

  useEffect(() => {
    if (!('speechSynthesis' in window)) return;
    const loadVoices = () => {
      voicesRef.current = window.speechSynthesis.getVoices();
    };
    loadVoices();
    window.speechSynthesis.addEventListener('voiceschanged', loadVoices);
    return () => window.speechSynthesis.removeEventListener('voiceschanged', loadVoices);
  }, []);

  useEffect(() => {
    const handleSpeak = (event: Event) => {
      const text = (event as CustomEvent<string>).detail;
      if (enabledRef.current && text) speak(text);
    };
    window.addEventListener('zeusex-speak', handleSpeak);
    return () => window.removeEventListener('zeusex-speak', handleSpeak);
  }, [speak]);

  const disable = useCallback(() => {
    enabledRef.current = false;
    setEnabled(false);
    setStatus('off');
    stopRecognition();
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  }, [stopRecognition]);

  const enable = useCallback(() => {
    const Constructor = recognitionConstructor();
    if (!Constructor) {
      setStatus('unsupported');
      return;
    }

    const recognition = recognitionRef.current ?? new Constructor();
    recognition.lang = 'pt-BR';
    recognition.continuous = true;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      if (busyRef.current || pausedRef.current) return;
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (!result.isFinal) continue;
        const transcript = result[0]?.transcript?.trim() ?? '';
        if (!normalize(transcript).includes('ei james')) continue;

        const match = transcript.match(/ei\s+james/i);
        const command = match
          ? transcript.slice((match.index ?? 0) + match[0].length).trim()
          : '';

        if (command) {
          window.dispatchEvent(new CustomEvent('zeusex-voice-command', { detail: command }));
        } else {
          window.dispatchEvent(new CustomEvent('zeusex-fill-chat', { detail: '' }));
          speak('Sim, senhor?');
        }
      }
    };

    recognition.onerror = (event) => {
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setStatus('blocked');
        enabledRef.current = false;
        setEnabled(false);
      }
    };

    recognition.onend = () => {
      if (enabledRef.current && !pausedRef.current && !busyRef.current) {
        window.setTimeout(startRecognition, 350);
      }
    };

    recognitionRef.current = recognition;
    enabledRef.current = true;
    setEnabled(true);
    setStatus('listening');
    startRecognition();
    speak('Escuta contínua ativada. Diga Ei James, senhor.');
  }, [speak, startRecognition]);

  useEffect(() => disable, [disable]);

  const label =
    status === 'listening' ? 'Ouvindo: Ei James'
      : status === 'speaking' ? 'James falando'
        : status === 'blocked' ? 'Microfone bloqueado'
          : status === 'unsupported' ? 'Voz indisponível'
            : 'Ativar Ei James';

  return (
    <button
      type="button"
      onClick={enabled ? disable : enable}
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs transition-colors cursor-pointer"
      style={{
        color: enabled ? 'var(--color-accent)' : 'var(--color-text-tertiary)',
        border: `1px solid ${enabled ? 'var(--color-accent)' : 'var(--color-border)'}`,
        background: enabled ? 'var(--color-accent-subtle)' : 'transparent',
      }}
      title={status === 'blocked' ? 'Permita o microfone nas configurações do navegador' : label}
      aria-pressed={enabled}
    >
      {enabled ? <AudioLines size={15} /> : <MicOff size={15} />}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}
