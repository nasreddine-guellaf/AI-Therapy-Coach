import { AvatarPanel } from "@/components/AvatarPanel";
import { ChatInterface } from "@/components/ChatInterface";

export default function Home() {
  return <main><header><h1>Therapeutic AI Coach</h1><p>Un espace de coaching et d'écoute — pas un service médical.</p></header><div className="workspace"><AvatarPanel /><ChatInterface /></div><footer>En situation de crise ou de danger immédiat, contactez les services d'urgence locaux.</footer></main>;
}
