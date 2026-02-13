'use client';

/**
 * Authentication context for ScholaRAG_Graph.
 * 
 * Provides user state and auth methods throughout the app.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { 
  supabase, 
  isSupabaseConfigured,
  signIn as supabaseSignIn,
  signUp as supabaseSignUp,
  signOut as supabaseSignOut,
  signInWithOAuth as supabaseSignInWithOAuth,
  resetPassword as supabaseResetPassword,
} from './supabase';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  isConfigured: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, fullName?: string) => Promise<void>;
  signOut: () => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signInWithGithub: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const isConfigured = isSupabaseConfigured();

  // Initialize auth state
  useEffect(() => {
    if (!supabase) {
      setIsLoading(false);
      return;
    }

    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setIsLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
        setIsLoading(false);
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const data = await supabaseSignIn(email, password);
      if (data.session) {
        setSession(data.session);
        setUser(data.session.user ?? null);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const signUp = useCallback(async (email: string, password: string, fullName?: string) => {
    setIsLoading(true);
    try {
      const data = await supabaseSignUp(email, password, fullName);
      if (data.session) {
        setSession(data.session);
        setUser(data.session.user ?? null);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    setIsLoading(true);
    try {
      await supabaseSignOut();
      setUser(null);
      setSession(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const signInWithGoogle = useCallback(async () => {
    await supabaseSignInWithOAuth('google');
  }, []);

  const signInWithGithub = useCallback(async () => {
    await supabaseSignInWithOAuth('github');
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    await supabaseResetPassword(email);
  }, []);

  const value: AuthContextType = {
    user,
    session,
    isLoading,
    isConfigured,
    signIn,
    signUp,
    signOut,
    signInWithGoogle,
    signInWithGithub,
    resetPassword,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

/**
 * Hook to require authentication
 * Redirects to login if not authenticated
 */
export function useRequireAuth(redirectTo: string = '/auth/login') {
  const { user, isLoading, isConfigured } = useAuth();

  useEffect(() => {
    if (!isLoading && isConfigured && !user) {
      window.location.href = redirectTo;
    }
  }, [user, isLoading, isConfigured, redirectTo]);

  return { user, isLoading };
}
