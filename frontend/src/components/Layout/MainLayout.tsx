import { ReactNode } from 'react';
import { Link } from '@remix-run/react';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="container mx-auto px-4">
          <div className="flex justify-between h-16">
            <div className="flex">
              <Link to="/" className="flex items-center">
                <span className="text-xl font-bold text-gray-900">
                  Vitalyst Knowledge Graph
                </span>
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <Link to="/graph" className="nav-link">
                Graph View
              </Link>
              <Link to="/search" className="nav-link">
                Search
              </Link>
              <Link to="/data" className="nav-link">
                Data Management
              </Link>
            </div>
          </div>
        </div>
      </nav>
      <main className="container mx-auto px-4 py-8">
        {children}
      </main>
      <footer className="bg-white border-t">
        <div className="container mx-auto px-4 py-6">
          <p className="text-center text-gray-600">
            © {new Date().getFullYear()} Vitalyst Knowledge Graph. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
} 