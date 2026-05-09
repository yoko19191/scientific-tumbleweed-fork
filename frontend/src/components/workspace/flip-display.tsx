import { AnimatePresence, motion } from "motion/react";

import { cn } from "@/lib/utils";

export function FlipDisplay({
  uniqueKey,
  children,
  className,
  innerClassName,
}: {
  uniqueKey: string;
  children: React.ReactNode;
  className?: string;
  innerClassName?: string;
}) {
  return (
    <div className={cn("relative overflow-hidden", className)}>
      <AnimatePresence mode="wait">
        <motion.div
          key={uniqueKey}
          className={cn(innerClassName)}
          initial={{ y: 8, opacity: 0 }}
          animate={{ y: 2, opacity: 1 }}
          exit={{ y: -8, opacity: 0 }}
          transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
