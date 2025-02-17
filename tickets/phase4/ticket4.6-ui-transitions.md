# Ticket 4.6: Implement UI Transitions & Animations

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement smooth and performant UI transitions and animations for the Vitalyst Knowledge Graph frontend, enhancing user experience while maintaining application performance. This includes slide-in/out animations for panels, status transitions, loading states, and graph interactions. All animations must follow the specifications in the blueprint for consistent visual feedback and accessibility.

## Technical Details
1. Animation System Implementation
```typescript
// src/styles/animations/index.ts
import { keyframes, css } from '@emotion/react';

export const slideIn = keyframes`
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
`;

export const fadeIn = keyframes`
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
`;

export const pulse = keyframes`
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
`;

// Animation utilities with performance optimizations
export const createTransition = (
  properties: string[],
  duration = 300,
  easing = 'cubic-bezier(0.4, 0, 0.2, 1)'
) => properties.map(prop => `${prop} ${duration}ms ${easing}`).join(', ');

export const performanceOptimizedAnimation = css`
  will-change: transform, opacity;
  backface-visibility: hidden;
  perspective: 1000px;
  transform: translateZ(0);
`;
```

2. Animated Components Implementation
```typescript
// src/components/transitions/SlidePanel.tsx
import { motion, AnimatePresence } from 'framer-motion';
import { PropsWithChildren } from 'react';
import { useReducedMotion } from '../../hooks/useReducedMotion';

interface SlidePanelProps {
  isOpen: boolean;
  onClose: () => void;
  position?: 'left' | 'right';
}

export const SlidePanel = ({
  isOpen,
  onClose,
  position = 'right',
  children
}: PropsWithChildren<SlidePanelProps>) => {
  const prefersReducedMotion = useReducedMotion();
  
  const variants = {
    initial: {
      x: position === 'right' ? '100%' : '-100%',
      opacity: 0
    },
    animate: {
      x: 0,
      opacity: 1,
      transition: {
        type: 'spring',
        damping: 25,
        stiffness: 180
      }
    },
    exit: {
      x: position === 'right' ? '100%' : '-100%',
      opacity: 0,
      transition: {
        type: 'spring',
        damping: 25,
        stiffness: 180
      }
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className={`slide-panel ${position}`}
            variants={prefersReducedMotion ? {} : variants}
            initial="initial"
            animate="animate"
            exit="exit"
            role="dialog"
            aria-modal="true"
          >
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

// src/components/transitions/StatusTransition.tsx
import { motion } from 'framer-motion';
import { ValidationStatus } from '../../types';

interface StatusTransitionProps {
  status: ValidationStatus;
  animate?: boolean;
}

export const StatusTransition = ({ status, animate = true }: StatusTransitionProps) => {
  const statusColors = {
    draft: '#9CA3AF',
    pending_review: '#FCD34D',
    approved: '#34D399',
    rejected: '#EF4444',
    needs_revision: '#F97316'
  };

  return (
    <motion.div
      className="status-indicator"
      initial={false}
      animate={{
        backgroundColor: statusColors[status],
        scale: animate ? [1, 1.1, 1] : 1
      }}
      transition={{
        duration: 0.3,
        scale: {
          duration: 0.2,
          repeat: animate ? 1 : 0
        }
      }}
    >
      {status}
    </motion.div>
  );
};
```

3. Graph Animation Implementation
```typescript
// src/components/graph/AnimatedNode.tsx
import { memo } from 'react';
import { motion } from 'framer-motion';
import { Handle, Position } from 'reactflow';

interface AnimatedNodeProps {
  data: any;
  selected: boolean;
}

export const AnimatedNode = memo(({ data, selected }: AnimatedNodeProps) => {
  return (
    <motion.div
      className={`node ${selected ? 'selected' : ''}`}
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ 
        scale: selected ? 1.1 : 1,
        opacity: 1,
        boxShadow: selected 
          ? '0 0 0 2px #3B82F6' 
          : '0 1px 3px rgba(0,0,0,0.1)'
      }}
      transition={{
        type: 'spring',
        damping: 15,
        stiffness: 300
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div className="node-content">
        <StatusTransition status={data.validation_status} />
        <h3>{data.name}</h3>
        <p>{data.type}</p>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </motion.div>
  );
});
```

4. Loading States Implementation
```typescript
// src/components/loading/LoadingSpinner.tsx
import { motion } from 'framer-motion';

export const LoadingSpinner = () => {
  return (
    <motion.div
      className="loading-spinner"
      animate={{
        rotate: 360
      }}
      transition={{
        duration: 1,
        repeat: Infinity,
        ease: 'linear'
      }}
      role="progressbar"
      aria-label="Loading"
    >
      <svg viewBox="0 0 50 50">
        <circle
          cx="25"
          cy="25"
          r="20"
          fill="none"
          strokeWidth="4"
          stroke="currentColor"
          strokeLinecap="round"
        />
      </svg>
    </motion.div>
  );
};
```

## Acceptance Criteria
- [ ] Smooth slide animations for panel transitions
- [ ] Status change animations with proper visual feedback
- [ ] Loading state animations for async operations
- [ ] Graph node animations for selection and updates
- [ ] Reduced motion support for accessibility
- [ ] Performance optimization for animations
- [ ] Consistent animation timing and easing
- [ ] Proper ARIA attributes for animated elements

## Dependencies
- Ticket 4.1: Frontend Setup
- Ticket 4.2: Interactive Dashboard
- Ticket 4.3: Detail Panel
- Ticket 4.5: Frontend Testing

## Estimated Hours
10

## Testing Requirements
- Animation Tests:
  - Verify animation timing and easing
  - Test reduced motion preferences
  - Validate performance metrics
- Integration Tests:
  - Test animation triggers
  - Verify state transitions
  - Test accessibility features
- Performance Tests:
  - Measure frame rates
  - Test animation impact on CPU
  - Verify memory usage
- Accessibility Tests:
  - Test with screen readers
  - Verify reduced motion support
  - Validate ARIA attributes

## Documentation
- Animation system overview
- Performance optimization guidelines
- Accessibility considerations
- Animation timing specifications
- Reduced motion implementation
- Component animation API

## References
- **Phasedplan.md:** Phase 4, Ticket 4.6
- **Blueprint.md:** Sections on UI/UX & CX, Frontend Development
- Framer Motion documentation
- Web Animations API specifications
- WCAG Animation Guidelines

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the UI transitions and animations as specified in the blueprint, with particular attention to:
- Smooth and performant animations
- Accessibility requirements
- Consistent visual feedback
- Performance optimization
- Reduced motion support
- Component reusability
``` 