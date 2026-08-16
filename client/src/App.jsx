import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';

import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';

import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import AuthCallbackPage from './pages/AuthCallbackPage';
import DashboardPage from './pages/DashboardPage';
import InboxPage from './pages/InboxPage';
import ClassifierLabPage from './pages/ClassifierLabPage';
import AnalyticsPage from './pages/AnalyticsPage';
import ProfilePage from './pages/ProfilePage';
import AdminPage from './pages/AdminPage';

function ProtectedRoute({ children, adminOnly = false }) {
  const { isAuthenticated, user, isLoading, token } = useAuth();

  // Still verifying — show spinner (but only if we actually have a token; no token = go to login)
  if (isLoading && token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-200">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-blue-600/20 border-t-blue-600 rounded-full animate-spin" />
          <p className="text-sm font-medium">Authenticating user session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function MainLayout() {
  const { user } = useAuth();
  const [activeFolder, setActiveFolder] = useState('inbox');
  const [activeCategory, setActiveCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans">
      <Navbar 
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        toggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />

      <div className="flex-1 flex max-w-[1600px] w-full mx-auto p-4 gap-4 overflow-hidden">
        <Sidebar 
          activeFolder={activeFolder}
          setActiveFolder={setActiveFolder}
          activeCategory={activeCategory}
          setActiveCategory={setActiveCategory}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          isAdmin={user?.role === 'admin'}
        />

        <main className="flex-1 overflow-y-auto pb-12">
          <Routes>
            <Route 
              path="/dashboard" 
              element={
                <DashboardPage 
                  setActiveCategory={setActiveCategory} 
                  setActiveFolder={setActiveFolder} 
                />
              } 
            />
            <Route 
              path="/" 
              element={
                <InboxPage 
                  activeFolder={activeFolder}
                  setActiveFolder={setActiveFolder}
                  activeCategory={activeCategory}
                  setActiveCategory={setActiveCategory}
                  searchQuery={searchQuery}
                />
              } 
            />
            <Route 
              path="/inbox" 
              element={
                <InboxPage 
                  activeFolder={activeFolder}
                  setActiveFolder={setActiveFolder}
                  activeCategory={activeCategory}
                  setActiveCategory={setActiveCategory}
                  searchQuery={searchQuery}
                />
              } 
            />
            <Route path="/classifier-lab" element={<ClassifierLabPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route 
              path="/admin" 
              element={
                <ProtectedRoute adminOnly>
                  <AdminPage />
                </ProtectedRoute>
              } 
            />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <MainLayout />
                </ProtectedRoute>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
