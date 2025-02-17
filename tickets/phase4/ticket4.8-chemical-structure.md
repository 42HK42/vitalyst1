# Ticket 4.8: Chemical Structure Visualization

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement a comprehensive chemical structure visualization system for the Vitalyst Knowledge Graph frontend that renders 2D and 3D molecular structures, supports SMILES notation, integrates with PubChem and PharmaGKB, and provides interactive molecular viewing capabilities. The system must support multiple visualization modes, handle complex molecular structures, provide fallback mechanisms, and maintain optimal performance while ensuring accessibility as specified in the blueprint.

## Technical Details
1. Molecular Viewer Component Implementation
```typescript
// src/components/chemical/MolecularViewer.tsx
import { memo, useEffect, useRef, useState } from 'react';
import { RDKit } from '@rdkit/rdkit';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { useAccessibility } from '../../hooks/useAccessibility';
import { useStructureCache } from '../../hooks/useStructureCache';
import { useMoleculeStore } from '../../stores/moleculeStore';
import { LoadingSpinner } from '../loading/LoadingSpinner';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { MoleculeControls } from './MoleculeControls';
import { MoleculeInfo } from './MoleculeInfo';
import { usePerformanceMonitor } from '../../hooks/usePerformanceMonitor';
import './MolecularViewer.css';

interface MolecularViewerProps {
  smiles: string;
  width?: number;
  height?: number;
  interactive?: boolean;
  viewMode?: '2d' | '3d';
  showControls?: boolean;
  showInfo?: boolean;
  onError?: (error: Error) => void;
}

export const MolecularViewer = memo(({
  smiles,
  width = 400,
  height = 300,
  interactive = true,
  viewMode = '2d',
  showControls = true,
  showInfo = true,
  onError
}: MolecularViewerProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const { prefersReducedMotion } = useAccessibility();
  const { trackRender } = usePerformanceMonitor();
  const { getCachedStructure, cacheStructure } = useStructureCache();
  const { updateMolecule } = useMoleculeStore();

  // Fetch PubChem data
  const { data: pubchemData } = useQuery({
    queryKey: ['pubchem', smiles],
    queryFn: () => fetchPubChemData(smiles),
    enabled: showInfo
  });

  useEffect(() => {
    const renderMolecule = async () => {
      const startTime = performance.now();
      try {
        setLoading(true);
        setError(null);

        // Check cache first
        const cached = await getCachedStructure(smiles);
        if (cached) {
          if (canvasRef.current) {
            const ctx = canvasRef.current.getContext('2d');
            if (ctx) {
              ctx.putImageData(cached, 0, 0);
              setLoading(false);
              return;
            }
          }
        }

        // Initialize RDKit
        const rdkit = await RDKit.load();
        const mol = rdkit.get_mol(smiles);
        
        if (canvasRef.current) {
          const ctx = canvasRef.current.getContext('2d');
          if (ctx) {
            // Configure rendering options
            const options = {
              width,
              height,
              bondLineWidth: 1.5,
              addStereoAnnotation: true,
              atomLabelSize: 14,
              backgroundColor: '#ffffff',
              highlightColor: '#3b82f6',
              ...getAccessibleColors()
            };

            if (viewMode === '2d') {
              mol.draw_to_canvas(ctx, options);
            } else {
              mol.draw_to_canvas_3d(ctx, {
                ...options,
                rotationDegrees: 0,
                perspective: 30
              });
            }

            // Cache the rendered structure
            const imageData = ctx.getImageData(0, 0, width, height);
            await cacheStructure(smiles, imageData);

            // Update molecule store
            updateMolecule({
              smiles,
              formula: mol.get_formula(),
              weight: mol.get_molecular_weight(),
              inchiKey: mol.get_inchi_key()
            });
          }
        }
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to render molecule');
        setError(error);
        onError?.(error);
      } finally {
        setLoading(false);
        trackRender('molecule', performance.now() - startTime);
      }
    };

    renderMolecule();
  }, [smiles, width, height, viewMode]);

  if (loading) {
    return <LoadingSpinner size="large" />;
  }

  if (error) {
    return (
      <div className="molecular-viewer-error" role="alert">
        <p>{error.message}</p>
        <div className="fallback-view">
          <pre className="smiles-notation" role="img" aria-label="Molecular structure in SMILES notation">
            {smiles}
          </pre>
          {pubchemData && (
            <MoleculeInfo 
              data={pubchemData}
              showStructure={false}
            />
          )}
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary
      fallback={
        <div className="molecular-viewer-error">
          <p>Failed to render molecular structure</p>
          <pre className="smiles-notation">{smiles}</pre>
        </div>
      }
    >
      <motion.div
        className="molecular-viewer"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ 
          duration: prefersReducedMotion ? 0 : 0.3 
        }}
      >
        <div className="canvas-container">
          <canvas
            ref={canvasRef}
            width={width}
            height={height}
            className={interactive ? 'interactive' : ''}
            role="img"
            aria-label={`Molecular structure of compound with SMILES notation: ${smiles}`}
          />
          {interactive && showControls && (
            <AnimatePresence>
              <MoleculeControls
                viewMode={viewMode}
                onZoom={handleZoom}
                onRotate={handleRotate}
                onReset={handleReset}
              />
            </AnimatePresence>
          )}
        </div>

        {showInfo && pubchemData && (
          <MoleculeInfo 
            data={pubchemData}
            className="molecule-details"
          />
        )}
      </motion.div>
    </ErrorBoundary>
  );
});

// src/components/chemical/MoleculeControls.tsx
interface MoleculeControlsProps {
  viewMode: '2d' | '3d';
  onZoom: (factor: number) => void;
  onRotate: (degrees: number) => void;
  onReset: () => void;
}

export const MoleculeControls = memo(({
  viewMode,
  onZoom,
  onRotate,
  onReset
}: MoleculeControlsProps) => {
  return (
    <motion.div
      className="molecule-controls"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
    >
      <button
        onClick={() => onZoom(1.2)}
        className="control-button"
        aria-label="Zoom in"
      >
        <ZoomInIcon />
      </button>
      <button
        onClick={() => onZoom(0.8)}
        className="control-button"
        aria-label="Zoom out"
      >
        <ZoomOutIcon />
      </button>
      {viewMode === '3d' && (
        <>
          <button
            onClick={() => onRotate(-90)}
            className="control-button"
            aria-label="Rotate left"
          >
            <RotateLeftIcon />
          </button>
          <button
            onClick={() => onRotate(90)}
            className="control-button"
            aria-label="Rotate right"
          >
            <RotateRightIcon />
          </button>
        </>
      )}
      <button
        onClick={onReset}
        className="control-button"
        aria-label="Reset view"
      >
        <ResetIcon />
      </button>
    </motion.div>
  );
});
```

2. PubChem Integration Implementation
```typescript
// src/services/pubchem.ts
import { ApiResponse, PubChemCompound } from '../types';
import { handleApiError } from '../utils/errorHandling';

export class PubChemAPI {
  private baseUrl = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug';
  private cache = new Map<string, PubChemCompound>();

  async getCompoundByCID(cid: string): Promise<ApiResponse<PubChemCompound>> {
    try {
      // Check cache first
      if (this.cache.has(cid)) {
        return {
          data: this.cache.get(cid)!,
          status: 200
        };
      }

      const response = await fetch(
        `${this.baseUrl}/compound/cid/${cid}/JSON`,
        {
          headers: {
            'Accept': 'application/json',
            'User-Agent': 'Vitalyst-KnowledgeGraph/1.0'
          }
        }
      );
      
      if (!response.ok) {
        throw new Error(`Failed to fetch compound data: ${response.statusText}`);
      }

      const data = await response.json();
      const compound = this.transformPubChemResponse(data);
      
      // Cache the result
      this.cache.set(cid, compound);

      return {
        data: compound,
        status: response.status
      };
    } catch (error) {
      return handleApiError(error);
    }
  }

  async searchBySmiles(smiles: string): Promise<ApiResponse<PubChemCompound[]>> {
    try {
      const response = await fetch(
        `${this.baseUrl}/compound/smiles/${encodeURIComponent(smiles)}/JSON`,
        {
          headers: {
            'Accept': 'application/json',
            'User-Agent': 'Vitalyst-KnowledgeGraph/1.0'
          }
        }
      );
      
      if (!response.ok) {
        throw new Error(`Failed to search compound: ${response.statusText}`);
      }

      const data = await response.json();
      const compounds = data.PC_Compounds.map(this.transformPubChemResponse);

      return {
        data: compounds,
        status: response.status
      };
    } catch (error) {
      return handleApiError(error);
    }
  }

  private transformPubChemResponse(data: any): PubChemCompound {
    return {
      cid: data.id.id.cid,
      smiles: this.findProperty(data, 'SMILES'),
      iupacName: this.findProperty(data, 'IUPAC Name'),
      molecularFormula: this.findProperty(data, 'Molecular Formula'),
      molecularWeight: this.findProperty(data, 'Molecular Weight'),
      inchiKey: this.findProperty(data, 'InChIKey'),
      synonyms: this.findProperty(data, 'Synonyms') || [],
      properties: {
        logP: this.findProperty(data, 'Log P'),
        hydrogenBondDonors: this.findProperty(data, 'Hydrogen Bond Donor Count'),
        hydrogenBondAcceptors: this.findProperty(data, 'Hydrogen Bond Acceptor Count'),
        rotatableBonds: this.findProperty(data, 'Rotatable Bond Count'),
        polarSurfaceArea: this.findProperty(data, 'Topological Polar Surface Area')
      }
    };
  }

  private findProperty(data: any, propertyName: string): any {
    return data.props?.find((p: any) => p.urn.label === propertyName)?.value?.sval;
  }
}
```

3. Structure Caching Implementation
```typescript
// src/services/structureCache.ts
import { openDB, DBSchema, IDBPDatabase } from 'idb';

interface StructureDB extends DBSchema {
  structures: {
    key: string;
    value: {
      imageData: ImageData;
      timestamp: number;
    };
  };
}

export class StructureCache {
  private db: IDBPDatabase<StructureDB> | null = null;
  private readonly dbName = 'molecular-structures';
  private readonly storeName = 'structures';
  private readonly version = 1;
  private readonly maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days

  async initialize(): Promise<void> {
    this.db = await openDB<StructureDB>(this.dbName, this.version, {
      upgrade(db) {
        db.createObjectStore('structures');
      }
    });
  }

  async set(smiles: string, imageData: ImageData): Promise<void> {
    if (!this.db) await this.initialize();

    await this.db!.put(this.storeName, {
      imageData,
      timestamp: Date.now()
    }, smiles);
  }

  async get(smiles: string): Promise<ImageData | null> {
    if (!this.db) await this.initialize();

    const entry = await this.db!.get(this.storeName, smiles);
    if (!entry) return null;

    if (Date.now() - entry.timestamp > this.maxAge) {
      await this.delete(smiles);
      return null;
    }

    return entry.imageData;
  }

  async delete(smiles: string): Promise<void> {
    if (!this.db) await this.initialize();
    await this.db!.delete(this.storeName, smiles);
  }

  async clear(): Promise<void> {
    if (!this.db) await this.initialize();
    await this.db!.clear(this.storeName);
  }
}
```

4. Styling Implementation
```css
/* src/styles/MolecularViewer.css */
.molecular-viewer {
  position: relative;
  background: var(--surface-color);
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 1rem;
  overflow: hidden;
}

.canvas-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 200px;
}

.molecular-viewer canvas {
  display: block;
  margin: 0 auto;
  touch-action: none;
}

.molecular-viewer.interactive canvas {
  cursor: grab;
}

.molecular-viewer.interactive canvas:active {
  cursor: grabbing;
}

.molecule-controls {
  position: absolute;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem;
  background: var(--surface-color);
  border-radius: 9999px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.control-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  padding: 0.5rem;
  border: none;
  border-radius: 50%;
  background: var(--surface-secondary);
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.control-button:hover {
  background: var(--surface-hover);
}

.control-button:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 2px;
}

.molecular-viewer-error {
  padding: 1rem;
  border: 1px solid var(--error-color);
  border-radius: 8px;
  background: var(--error-bg);
  color: var(--error-color);
}

.fallback-view {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--surface-secondary);
  border-radius: 4px;
}

.smiles-notation {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.molecule-details {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

@media (prefers-reduced-motion: reduce) {
  .molecular-viewer,
  .control-button {
    transition: none;
  }
}

@media (max-width: 640px) {
  .molecule-controls {
    bottom: 0.5rem;
  }

  .control-button {
    width: 2rem;
    height: 2rem;
  }
}
```

## Implementation Strategy
1. Core Functionality
   - Implement molecular viewer component
   - Set up RDKit integration
   - Configure 2D/3D rendering
   - Implement interactive controls

2. External Integration
   - Set up PubChem API client
   - Implement data transformation
   - Configure caching system
   - Handle API errors

3. Performance & Caching
   - Implement structure caching
   - Optimize rendering performance
   - Configure memory management
   - Set up performance monitoring

4. Accessibility & UX
   - Add ARIA attributes
   - Implement keyboard controls
   - Configure screen reader support
   - Add reduced motion support

## Acceptance Criteria
- [ ] 2D structure visualization with RDKit
- [ ] 3D structure visualization support
- [ ] SMILES notation parsing and display
- [ ] PubChem integration and data fetching
- [ ] Interactive molecular controls
- [ ] Structure caching system
- [ ] Fallback display mechanisms
- [ ] Accessibility features
- [ ] Performance optimization
- [ ] Error handling
- [ ] Loading states
- [ ] Documentation
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance tests

## Dependencies
- Ticket 4.1: Frontend Setup
- Ticket 4.2: Interactive Dashboard
- Ticket 4.4: API Client
- Ticket 3.2: Core API Endpoints

## Estimated Hours
25

## Testing Requirements
- Unit Tests:
  - Test molecular rendering
  - Verify control functions
  - Test PubChem integration
  - Validate caching
  - Test error handling
  - Verify accessibility

- Integration Tests:
  - Test RDKit integration
  - Verify PubChem API
  - Test caching system
  - Validate user interactions
  - Test error recovery

- Performance Tests:
  - Measure render times
  - Test memory usage
  - Verify caching efficiency
  - Test large molecules
  - Monitor WebGL performance

- Accessibility Tests:
  - Test keyboard navigation
  - Verify screen readers
  - Test color contrast
  - Validate ARIA labels
  - Test reduced motion

## Documentation
- Component API reference
- RDKit integration guide
- PubChem API documentation
- Caching implementation
- Performance optimization
- Accessibility features
- Testing procedures
- Error handling
- Upgrade procedures
- User interaction guide

## Search Space Optimization
- Clear component hierarchy
- Consistent naming patterns
- Standardized prop interfaces
- Logical file organization
- Well-documented utilities
- Organized test structure
- Clear state management
- Consistent styling patterns
- Standardized API interfaces
- Organized cache handlers

## References
- **Phasedplan.md:** Phase 4, Ticket 4.8
- **Blueprint.md:** Sections on Chemical Structure Visualization
- RDKit Documentation
- PubChem API Guidelines
- WebGL Best Practices
- WCAG Accessibility Guidelines

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the chemical structure visualization system as specified in the blueprint, with particular attention to:
- Comprehensive structure rendering
- External API integration
- Performance optimization
- Accessibility compliance
- User experience
- Error handling
- Documentation standards
- Testing coverage
- Maintenance procedures
- Search space optimization
``` 