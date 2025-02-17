# Ticket 4.12: Chemical Structure Visualization Optimization

## Priority
High

## Type
Development

## Status
To Do

## Description
Optimize the chemical structure visualization system for the Vitalyst Knowledge Graph frontend by implementing efficient 2D/3D structure caching, intelligent fallback mechanisms, simplified views for non-expert users, and comprehensive accessibility features. The system must maintain high performance while providing accessible and user-friendly molecular visualization with real-time updates and optimal memory management as specified in the blueprint.

## Technical Details
1. Structure Caching Service Implementation
```typescript
// src/services/StructureCacheService.ts
import { LRUCache } from 'lru-cache';
import { RDKit } from '@rdkit/rdkit';
import { StorageService } from './StorageService';
import { usePerformanceMonitor } from '../hooks/usePerformanceMonitor';
import { useWebSocket } from '../hooks/useWebSocket';
import { useErrorBoundary } from '../hooks/useErrorBoundary';

interface CacheEntry {
  svg2D: string;
  svg3D?: string;
  molData: {
    smiles: string;
    inchi: string;
    formula: string;
    mass: number;
    timestamp: number;
    hash: string;
    version: string;
  };
  renderMetrics: {
    renderTime: number;
    memoryUsage: number;
    complexity: number;
  };
}

interface CacheConfig {
  maxSize: number;
  maxAge: number;
  updateInterval: number;
  compressionLevel: number;
  storageStrategy: 'memory' | 'indexeddb' | 'hybrid';
}

export class StructureCacheService {
  private memoryCache: LRUCache<string, CacheEntry>;
  private storage: StorageService;
  private rdkit: typeof RDKit | null = null;
  private ws: WebSocket | null = null;
  private metrics: PerformanceMonitor;
  private errorBoundary: ErrorBoundary;

  constructor(config: CacheConfig) {
    this.memoryCache = new LRUCache({
      max: config.maxSize,
      maxAge: config.maxAge,
      updateAgeOnGet: true,
      updateAgeOnHas: true,
      dispose: (value, key) => this.handleCacheDisposal(value, key)
    });

    this.storage = new StorageService('chemical-structures', {
      compression: config.compressionLevel,
      strategy: config.storageStrategy
    });

    this.metrics = new PerformanceMonitor('structure-cache');
    this.errorBoundary = new ErrorBoundary();
    this.initializeWebSocket();
  }

  private initializeWebSocket() {
    this.ws = new WebSocket('ws://localhost:8000/ws/structures');
    this.ws.addEventListener('message', async (event) => {
      const update = JSON.parse(event.data);
      switch (update.type) {
        case 'structure_update':
          await this.handleStructureUpdate(update.data);
          break;
        case 'cache_invalidate':
          await this.invalidateCache(update.patterns);
          break;
      }
    });
  }

  async initialize(): Promise<void> {
    try {
      this.metrics.startOperation('init');
      this.rdkit = await RDKit.load();
      await this.loadPersistedCache();
      await this.preloadCommonStructures();
      this.metrics.endOperation('init');
    } catch (error) {
      this.errorBoundary.handleError('Initialization failed:', error);
      throw error;
    }
  }

  private async loadPersistedCache(): Promise<void> {
    const persistedEntries = await this.storage.getAll();
    for (const entry of persistedEntries) {
      if (this.isValidCacheEntry(entry)) {
        this.memoryCache.set(entry.molData.hash, entry);
      }
    }
  }

  private async preloadCommonStructures(): Promise<void> {
    const commonSmiles = await this.fetchCommonSmiles();
    await Promise.all(
      commonSmiles.map(smiles => this.generateStructure(smiles, true))
    );
  }

  async getStructure(
    smiles: string,
    options: {
      dimension: '2d' | '3d';
      size?: { width: number; height: number };
      simplified?: boolean;
      highQuality?: boolean;
    }
  ): Promise<string> {
    this.metrics.startOperation('get-structure');
    try {
      const hash = await this.generateHash(smiles);
      const cached = this.memoryCache.get(hash);

      if (cached) {
        this.metrics.recordHit('cache-hit');
        return options.dimension === '3d' ? cached.svg3D || cached.svg2D : cached.svg2D;
      }

      const svg = await this.generateStructure(smiles, options);
      this.metrics.recordHit('cache-miss');
      return svg;
    } catch (error) {
      this.errorBoundary.handleError('Structure generation failed:', error);
      return this.getFallbackStructure(smiles, options);
    } finally {
      this.metrics.endOperation('get-structure');
    }
  }

  private async generateStructure(
    smiles: string,
    options: {
      dimension: '2d' | '3d';
      size?: { width: number; height: number };
      simplified?: boolean;
      highQuality?: boolean;
    }
  ): Promise<string> {
    if (!this.rdkit) {
      throw new Error('RDKit not initialized');
    }

    const startTime = performance.now();
    const memoryBefore = performance.memory?.usedJSHeapSize;

    try {
      const mol = this.rdkit.get_mol(smiles);
      const svg = options.dimension === '3d'
        ? await this.generate3DSVG(mol, options)
        : await this.generate2DSVG(mol, options);

      const renderTime = performance.now() - startTime;
      const memoryUsage = performance.memory?.usedJSHeapSize - memoryBefore;

      const entry: CacheEntry = {
        svg2D: options.dimension === '2d' ? svg : await this.generate2DSVG(mol, options),
        svg3D: options.dimension === '3d' ? svg : undefined,
        molData: {
          smiles,
          inchi: mol.get_inchi(),
          formula: mol.get_formula(),
          mass: mol.get_exact_mw(),
          timestamp: Date.now(),
          hash: await this.generateHash(smiles),
          version: '1.0'
        },
        renderMetrics: {
          renderTime,
          memoryUsage: memoryUsage || 0,
          complexity: this.calculateComplexity(mol)
        }
      };

      await this.cacheEntry(entry);
      return svg;
    } catch (error) {
      throw new Error(`Failed to generate structure: ${error.message}`);
    }
  }

  private async getFallbackStructure(
    smiles: string,
    options: {
      dimension: '2d' | '3d';
      simplified?: boolean;
    }
  ): Promise<string> {
    try {
      if (options.simplified) {
        return this.generateSimplifiedView(smiles);
      }
      
      const fallbackOptions = {
        ...options,
        dimension: '2d' as const,
        highQuality: false
      };
      
      return this.generateStructure(smiles, fallbackOptions);
    } catch (error) {
      return this.generateTextFallback(smiles);
    }
  }

  private generateSimplifiedView(smiles: string): string {
    // Generate a simplified molecular representation
    // using basic SVG shapes and chemical formula
    return `<svg>...</svg>`;
  }

  private generateTextFallback(smiles: string): string {
    // Generate a text-based fallback with chemical formula
    // and basic structure information
    return `<svg>...</svg>`;
  }

  private async cacheEntry(entry: CacheEntry): Promise<void> {
    this.memoryCache.set(entry.molData.hash, entry);
    await this.storage.set(entry.molData.hash, entry);
  }

  private calculateComplexity(mol: any): number {
    return mol.get_num_atoms() * mol.get_num_bonds();
  }

  async clearCache(): Promise<void> {
    this.memoryCache.clear();
    await this.storage.clear();
  }

  getMetrics(): any {
    return this.metrics.getMetrics();
  }
}
```

2. Fallback Renderer Implementation
```typescript
// src/components/chemical/FallbackRenderer.tsx
import { memo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAccessibility } from '../../hooks/useAccessibility';
import { usePerformanceMonitor } from '../../hooks/usePerformanceMonitor';
import { SimplifiedMolecule } from './SimplifiedMolecule';
import { ChemicalFormula } from './ChemicalFormula';
import { MoleculeProperties } from './MoleculeProperties';
import './FallbackRenderer.css';

interface FallbackRendererProps {
  smiles: string;
  formula?: string;
  name?: string;
  properties?: {
    mass?: number;
    charge?: number;
    rings?: number;
  };
  error?: Error;
  onRetry?: () => void;
}

export const FallbackRenderer = memo(({
  smiles,
  formula,
  name,
  properties,
  error,
  onRetry
}: FallbackRendererProps) => {
  const { prefersReducedMotion } = useAccessibility();
  const { trackRender } = usePerformanceMonitor();

  useEffect(() => {
    trackRender('fallback-renderer');
  }, [trackRender]);

  return (
    <motion.div
      className="fallback-renderer"
      initial={prefersReducedMotion ? false : { opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      role="img"
      aria-label={`Chemical structure for ${name || formula || smiles}`}
    >
      <div className="fallback-header">
        {name && <h3>{name}</h3>}
        {formula && <ChemicalFormula formula={formula} />}
      </div>

      <SimplifiedMolecule 
        smiles={smiles}
        showBonds={true}
        showAtomLabels={true}
        interactive={true}
      />

      {properties && (
        <MoleculeProperties
          properties={properties}
          className="molecule-properties"
        />
      )}

      <div className="smiles-notation">
        <label>SMILES Notation:</label>
        <code>{smiles}</code>
      </div>

      {error && (
        <motion.div
          className="error-message"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <p>Unable to render detailed structure</p>
          <small>{error.message}</small>
          {onRetry && (
            <button
              onClick={onRetry}
              className="retry-button"
              aria-label="Retry structure generation"
            >
              Retry
            </button>
          )}
        </motion.div>
      )}
    </motion.div>
  );
});

// src/components/chemical/SimplifiedMolecule.tsx
interface SimplifiedMoleculeProps {
  smiles: string;
  showBonds?: boolean;
  showAtomLabels?: boolean;
  interactive?: boolean;
}

export const SimplifiedMolecule = memo(({
  smiles,
  showBonds = true,
  showAtomLabels = true,
  interactive = false
}: SimplifiedMoleculeProps) => {
  const atoms = parseSmiles(smiles);
  const bonds = showBonds ? calculateBonds(atoms) : [];
  
  return (
    <div 
      className={`simplified-molecule ${interactive ? 'interactive' : ''}`}
      role="img"
      aria-label="Simplified molecular structure"
    >
      <svg viewBox="0 0 200 200">
        {/* Render bonds */}
        {showBonds && bonds.map((bond, index) => (
          <line
            key={`bond-${index}`}
            x1={bond.start.x}
            y1={bond.start.y}
            x2={bond.end.x}
            y2={bond.end.y}
            className={`bond ${bond.type}`}
          />
        ))}
        
        {/* Render atoms */}
        {atoms.map((atom, index) => (
          <g
            key={`atom-${index}`}
            transform={`translate(${atom.x}, ${atom.y})`}
            className="atom"
          >
            <circle r={10} className={`atom-${atom.element.toLowerCase()}`} />
            {showAtomLabels && (
              <text
                className="atom-label"
                textAnchor="middle"
                dy=".3em"
              >
                {atom.element}
              </text>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
});
```

3. Performance Optimization Implementation
```typescript
// src/hooks/useStructureRenderer.ts
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useStructureCache } from './useStructureCache';
import { useRDKit } from './useRDKit';
import { usePerformanceMonitor } from './usePerformanceMonitor';
import { useErrorBoundary } from './useErrorBoundary';

interface RenderOptions {
  dimension?: '2d' | '3d';
  size?: { width: number; height: number };
  simplified?: boolean;
  highQuality?: boolean;
  interactive?: boolean;
}

export function useStructureRenderer(
  smiles: string,
  options: RenderOptions = {}
) {
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [retryCount, setRetryCount] = useState(0);

  const cache = useStructureCache();
  const rdkit = useRDKit();
  const { trackRender, trackError } = usePerformanceMonitor();
  const { handleError } = useErrorBoundary();

  const renderOptions = useMemo(() => ({
    dimension: options.dimension || '2d',
    size: options.size || { width: 300, height: 200 },
    simplified: options.simplified || false,
    highQuality: options.highQuality || false,
    interactive: options.interactive || false
  }), [options]);

  const renderStructure = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      trackRender('structure-render-start');

      // Try to get from cache first
      const cached = await cache.getStructure(smiles, renderOptions);
      if (cached) {
        setSvg(cached);
        trackRender('structure-render-cache-hit');
        return;
      }

      // Generate new rendering
      if (!rdkit.isReady) {
        throw new Error('RDKit not ready');
      }

      const mol = rdkit.getMolecule(smiles);
      const newSvg = await mol.toSVG(renderOptions);

      setSvg(newSvg);
      cache.setStructure(smiles, newSvg);
      trackRender('structure-render-success');
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to render structure');
      setError(error);
      trackError('structure-render-error', error);
      handleError(error);
    } finally {
      setLoading(false);
    }
  }, [smiles, renderOptions, cache, rdkit, trackRender, trackError, handleError]);

  const handleRetry = useCallback(() => {
    setRetryCount(count => count + 1);
    renderStructure();
  }, [renderStructure]);

  useEffect(() => {
    renderStructure();
  }, [renderStructure]);

  return {
    svg,
    error,
    loading,
    retryCount,
    handleRetry
  };
}
```

4. Accessibility Implementation
```typescript
// src/components/chemical/AccessibleStructure.tsx
import { memo, useRef, useEffect } from 'react';
import { useAccessibility } from '../../hooks/useAccessibility';
import { useKeyboard } from '../../hooks/useKeyboard';
import { useFocus } from '../../hooks/useFocus';
import { ChemicalDescription } from './ChemicalDescription';

interface AccessibleStructureProps {
  smiles: string;
  name?: string;
  formula?: string;
  description?: string;
  children: React.ReactNode;
}

export const AccessibleStructure = memo(({
  smiles,
  name,
  formula,
  description,
  children
}: AccessibleStructureProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { prefersReducedMotion } = useAccessibility();
  const { handleKeyDown } = useKeyboard();
  const { focusElement } = useFocus();

  useEffect(() => {
    if (containerRef.current) {
      focusElement(containerRef.current);
    }
  }, [focusElement]);

  return (
    <div
      ref={containerRef}
      className="accessible-structure"
      role="region"
      aria-label="Chemical structure viewer"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      <div className="structure-container">
        {children}
      </div>

      <ChemicalDescription
        name={name}
        formula={formula}
        smiles={smiles}
        description={description}
        prefersReducedMotion={prefersReducedMotion}
      />

      <div className="keyboard-instructions" aria-hidden="true">
        <p>Use arrow keys to navigate structure</p>
        <p>Press Space to toggle 2D/3D view</p>
        <p>Press + or - to zoom</p>
      </div>
    </div>
  );
});
```

## Implementation Strategy
1. Caching System
   - Implement LRU cache
   - Set up IndexedDB storage
   - Configure WebSocket updates
   - Implement cache invalidation

2. Fallback Mechanisms
   - Create simplified renderer
   - Implement text fallbacks
   - Set up error handling
   - Configure retry logic

3. Performance Optimization
   - Implement component memoization
   - Configure render tracking
   - Set up memory monitoring
   - Optimize WebSocket usage

4. Accessibility Features
   - Add ARIA attributes
   - Implement keyboard navigation
   - Configure screen reader support
   - Add reduced motion support

## Acceptance Criteria
- [ ] Efficient structure caching system
- [ ] Robust fallback mechanisms
- [ ] Real-time structure updates
- [ ] Memory usage optimization
- [ ] Performance monitoring
- [ ] Accessibility compliance
- [ ] Error recovery system
- [ ] Documentation
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance tests
- [ ] Accessibility tests

## Dependencies
- Ticket 4.8: Chemical Structure Visualization
- Ticket 4.1: Frontend Setup
- Ticket 3.2: Core API Endpoints

## Estimated Hours
25

## Testing Requirements
- Unit Tests:
  - Test caching system
  - Verify fallback rendering
  - Test WebSocket integration
  - Validate memory management
  - Test accessibility features
  - Verify error handling

- Integration Tests:
  - Test structure updates
  - Verify cache persistence
  - Test fallback flows
  - Validate state management
  - Test error recovery
  - Verify accessibility

- Performance Tests:
  - Measure render times
  - Test memory usage
  - Verify cache efficiency
  - Test WebSocket performance
  - Monitor resource usage
  - Validate optimization

- Accessibility Tests:
  - Test keyboard navigation
  - Verify screen readers
  - Test color contrast
  - Validate ARIA labels
  - Test reduced motion
  - Verify focus management

## Documentation
- Caching system overview
- Fallback mechanism guide
- Performance optimization
- Memory management
- Accessibility features
- WebSocket integration
- Error handling
- Testing procedures
- Upgrade guide
- User interaction guide

## Search Space Optimization
- Clear component hierarchy
- Consistent naming patterns
- Standardized interfaces
- Logical file organization
- Well-documented utilities
- Organized test structure
- Clear state management
- Consistent styling patterns
- Standardized caching patterns
- Organized WebSocket handlers

## References
- **Phasedplan.md:** Phase 4, Ticket 4.12
- **Blueprint.md:** Sections on Chemical Structure Visualization
- RDKit Documentation
- WebSocket Best Practices
- React Performance Guidelines
- WCAG Accessibility Guidelines

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the chemical structure optimization system as specified in the blueprint, with particular attention to:
- Efficient caching
- Robust fallbacks
- Performance optimization
- Memory management
- Real-time updates
- Accessibility compliance
- Error handling
- Documentation standards
- Testing coverage
- User experience 