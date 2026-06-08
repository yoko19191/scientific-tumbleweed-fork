import Image from "next/image";

import { BioAgentTerminalOverlay } from "./bio-agent-terminal-overlay";

const BIO_BACKGROUND = "/landing/bio-agent-hero-bg-balanced-01.webp";
const COMPUTER_CUTOUT =
  "/landing/bio-agent-hero-candidate-computer-cutout-01.png";
const DNA_RIBBON = "/landing/bio-agent-hero-dna-ribbon-cutout-01.png";

export function BioAgentHeroScene() {
  return (
    <div
      className="landing-reveal landing-bio-stage pointer-events-none relative lg:-mt-12"
      aria-label="Animated bio agent terminal in a retro laboratory scene"
    >
      <Image
        src={BIO_BACKGROUND}
        alt=""
        aria-hidden="true"
        fill
        priority
        sizes="(max-width: 1024px) 100vw, 50vw"
        className="landing-bio-stage-background"
      />
      <div className="landing-bio-stage-paper" aria-hidden="true" />
      <Image
        src={DNA_RIBBON}
        alt=""
        aria-hidden="true"
        fill
        sizes="(max-width: 1024px) 100vw, 58vw"
        className="landing-bio-dna-ribbon"
      />
      <div className="landing-bio-stage-shadow" aria-hidden="true" />
      <div className="landing-bio-computer-layer" aria-hidden="true">
        <Image
          src={COMPUTER_CUTOUT}
          alt=""
          fill
          priority
          sizes="(max-width: 900px) 86vw, 34rem"
          className="landing-bio-computer-image"
        />
        <div className="landing-crt-plane">
          <BioAgentTerminalOverlay />
        </div>
      </div>
      <div className="landing-bio-edge-softener" aria-hidden="true" />
    </div>
  );
}
