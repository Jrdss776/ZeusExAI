import { useEffect, useState } from 'react';
import { ChatArea } from '../components/Chat/ChatArea';
import { SecondBrain } from '../components/SecondBrain/SecondBrain';
import { SystemPanel } from '../components/Chat/SystemPanel';
import { useAppStore } from '../lib/store';

export function ChatPage() {
  const systemPanelOpen = useAppStore((s) => s.systemPanelOpen);
  const [brainOpen, setBrainOpen] = useState(false);

  useEffect(() => {
    const toggleBrain = () => setBrainOpen((open) => !open);
    window.addEventListener('zeusex-toggle-brain', toggleBrain);
    return () => window.removeEventListener('zeusex-toggle-brain', toggleBrain);
  }, []);

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex-1 min-w-0">
        <ChatArea />
      </div>
      {systemPanelOpen && <SystemPanel />}
      <SecondBrain open={brainOpen} onClose={() => setBrainOpen(false)} />
    </div>
  );
}
