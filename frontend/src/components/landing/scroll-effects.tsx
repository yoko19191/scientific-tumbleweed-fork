"use client";

import { useEffect } from "react";

export function LandingScrollEffects() {
    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("visible");
                    }
                });
            },
            { threshold: 0.1 }
        );

        document
            .querySelectorAll(".stitch-reveal")
            .forEach((el) => observer.observe(el));

        const handleScroll = () => {
            const tumbleweed = document.getElementById("tumbleweed-sprite");
            if (!tumbleweed) return;
            const scrollY = window.scrollY;
            const rotation = (scrollY * 0.4) % 360;
            const translateX = Math.sin(scrollY * 0.005) * 30;
            const translateY = Math.sin(scrollY * 0.01) * 10;
            tumbleweed.style.transform = `rotate(${rotation}deg) translate(${translateX}px, ${translateY}px)`;
            const container = tumbleweed.parentElement;
            if (container) {
                container.style.opacity = scrollY > 100 ? "1" : "0";
            }
        };

        window.addEventListener("scroll", handleScroll, { passive: true });

        return () => {
            observer.disconnect();
            window.removeEventListener("scroll", handleScroll);
        };
    }, []);

    return null;
}
