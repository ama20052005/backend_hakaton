import { motion } from 'motion/react';

export default function RussiaMap() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 1.1 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 1.5, ease: 'easeOut' }}
      className="w-full h-full relative"
    >
      <svg
        viewBox="0 0 1440 900"
        className="w-full h-full"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <radialGradient id="densityGlow" cx="55%" cy="45%">
            <stop offset="0%" stopColor="#006064" stopOpacity="0.25" />
            <stop offset="30%" stopColor="#00838F" stopOpacity="0.15" />
            <stop offset="70%" stopColor="#0097A7" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#00BCD4" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="mapGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#006064" stopOpacity="0.12" />
            <stop offset="50%" stopColor="#00838F" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#0097A7" stopOpacity="0.04" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Background glow layers */}
        <ellipse cx="800" cy="400" rx="650" ry="450" fill="url(#densityGlow)" opacity="0.8" />
        <ellipse cx="650" cy="380" rx="400" ry="300" fill="url(#densityGlow)" opacity="0.5" />

        {/* Stylized Russia map outline */}
        <motion.path
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 2.5, ease: 'easeInOut' }}
          d="M 280,420 Q 330,360 420,390 L 480,370 Q 540,345 610,370 L 720,360 Q 780,340 880,350 L 980,340 Q 1080,330 1140,365 L 1200,400 Q 1230,450 1190,500 L 1140,550 Q 1080,600 1020,590 L 920,580 Q 820,595 760,625 L 660,645 Q 560,660 500,640 L 400,615 Q 340,580 300,530 Q 260,480 280,420 Z"
          fill="url(#mapGradient)"
          stroke="#006064"
          strokeWidth="2.5"
          strokeOpacity="0.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Inner contour lines - modern topographic style */}
        <motion.path
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.25 }}
          transition={{ duration: 1.5, delay: 0.6 }}
          d="M 420,440 Q 480,420 580,432 L 680,427 Q 780,417 880,427 L 980,435 Q 1040,455 1010,490 L 940,520 Q 840,535 740,528 L 640,520 Q 530,530 470,505 Q 410,480 420,440 Z"
          fill="none"
          stroke="#006064"
          strokeWidth="1.5"
          strokeOpacity="0.3"
          strokeDasharray="6 8"
        />

        <motion.path
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.2 }}
          transition={{ duration: 1.5, delay: 0.8 }}
          d="M 480,465 Q 540,445 640,458 L 740,452 Q 840,445 940,458 L 990,470 Q 1020,495 985,525 L 900,545 Q 800,555 700,550 L 600,542 Q 520,548 490,525 Q 460,500 480,465 Z"
          fill="none"
          stroke="#00838F"
          strokeWidth="1.2"
          strokeOpacity="0.25"
          strokeDasharray="4 10"
        />

        {/* Major population centers with enhanced glow */}
        {[
          { x: 550, y: 475, r: 7, label: 'Москва', size: 1.2 },
          { x: 730, y: 465, r: 9, label: 'Урал', size: 1.4 },
          { x: 940, y: 485, r: 6, label: 'Сибирь', size: 1.0 },
          { x: 1090, y: 415, r: 5, label: 'Дальний Восток', size: 0.9 },
          { x: 450, y: 510, r: 5, label: 'Юг', size: 0.9 },
          { x: 680, y: 520, r: 6, label: 'Поволжье', size: 1.0 },
        ].map((point, i) => (
          <motion.g key={i} filter="url(#glow)">
            <motion.circle
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: point.size, opacity: 0.5 }}
              transition={{ duration: 1, delay: 1.2 + i * 0.12 }}
              cx={point.x}
              cy={point.y}
              r={point.r}
              fill="#006064"
            />
            <motion.circle
              initial={{ scale: 0, opacity: 0 }}
              animate={{
                scale: [point.size, point.size * 1.8, point.size],
                opacity: [0.3, 0, 0.3]
              }}
              transition={{
                duration: 4,
                delay: 1.8 + i * 0.12,
                repeat: Infinity,
                repeatDelay: 1.5
              }}
              cx={point.x}
              cy={point.y}
              r={point.r * 2.5}
              fill="none"
              stroke="#00838F"
              strokeWidth="2"
            />
          </motion.g>
        ))}

        {/* Minimal grid - very subtle */}
        <motion.g
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.02 }}
          transition={{ duration: 1.5, delay: 0.5 }}
        >
          {Array.from({ length: 10 }).map((_, i) => (
            <line
              key={`v-${i}`}
              x1={250 + i * 130}
              y1="300"
              x2={250 + i * 130}
              y2="650"
              stroke="#006064"
              strokeWidth="0.5"
            />
          ))}
          {Array.from({ length: 6 }).map((_, i) => (
            <line
              key={`h-${i}`}
              x1="250"
              y1={300 + i * 70}
              x2="1400"
              y2={300 + i * 70}
              stroke="#006064"
              strokeWidth="0.5"
            />
          ))}
        </motion.g>

        {/* Flowing data lines - animated */}
        <motion.g
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.15 }}
          transition={{ duration: 2, delay: 1 }}
        >
          <motion.path
            d="M 450,510 Q 550,490 650,500"
            fill="none"
            stroke="#00BCD4"
            strokeWidth="1.5"
            strokeDasharray="4 6"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 2, delay: 1.5, repeat: Infinity, repeatDelay: 3 }}
          />
          <motion.path
            d="M 730,465 Q 840,470 940,485"
            fill="none"
            stroke="#00BCD4"
            strokeWidth="1.5"
            strokeDasharray="4 6"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 2, delay: 2, repeat: Infinity, repeatDelay: 3 }}
          />
        </motion.g>
      </svg>
    </motion.div>
  );
}
