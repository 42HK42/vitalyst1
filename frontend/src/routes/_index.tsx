import { MainLayout } from '~/components/Layout/MainLayout';

export default function Index() {
  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-8">
          Welcome to Vitalyst Knowledge Graph
        </h1>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="card">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              Graph Visualization
            </h2>
            <p className="text-gray-600 mb-4">
              Explore the knowledge graph visually, discover relationships, and gain insights
              from the interconnected data.
            </p>
            <a href="/graph" className="btn btn-primary">
              Explore Graph
            </a>
          </div>
          
          <div className="card">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              Data Management
            </h2>
            <p className="text-gray-600 mb-4">
              Import, validate, and manage nutritional data with AI-powered enrichment
              and source verification.
            </p>
            <a href="/data" className="btn btn-primary">
              Manage Data
            </a>
          </div>
          
          <div className="card">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              Search
            </h2>
            <p className="text-gray-600 mb-4">
              Search through the knowledge graph using natural language queries and
              advanced filters.
            </p>
            <a href="/search" className="btn btn-primary">
              Search Data
            </a>
          </div>
          
          <div className="card">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              Documentation
            </h2>
            <p className="text-gray-600 mb-4">
              Access comprehensive documentation, API references, and usage guides
              for the system.
            </p>
            <a href="/docs" className="btn btn-primary">
              View Docs
            </a>
          </div>
        </div>
      </div>
    </MainLayout>
  );
} 