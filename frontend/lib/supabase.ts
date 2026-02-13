/**
 * Supabase client for ScholaRAG_Graph frontend.
 * 
 * Handles authentication state and API communication with Supabase.
 */

import { createClient, SupabaseClient, User, Session } from '@supabase/supabase-js';

// Environment variables
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

// Validate configuration with detailed error messages
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('❌ Supabase credentials not configured!');
  console.error('   Missing environment variables:');
  if (!supabaseUrl) console.error('   - NEXT_PUBLIC_SUPABASE_URL');
  if (!supabaseAnonKey) console.error('   - NEXT_PUBLIC_SUPABASE_ANON_KEY');
  console.error('');
  console.error('   To fix this:');
  console.error('   1. For local development: Create frontend/.env.local with these values');
  console.error('   2. For Vercel: Add environment variables in Project Settings → Environment Variables');
  console.error('');
  console.warn('   Auth features will be disabled until credentials are configured.');
}

// Create Supabase client
export const supabase: SupabaseClient | null = 
  supabaseUrl && supabaseAnonKey 
    ? createClient(supabaseUrl, supabaseAnonKey, {
        auth: {
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: true,
        },
      })
    : null;

/**
 * Check if Supabase is configured
 */
export function isSupabaseConfigured(): boolean {
  return supabase !== null;
}

/**
 * Get the current session
 */
export async function getSession(): Promise<Session | null> {
  if (!supabase) return null;
  
  const { data: { session } } = await supabase.auth.getSession();
  return session;
}

/**
 * Get the current user
 */
export async function getUser(): Promise<User | null> {
  if (!supabase) return null;
  
  const { data: { user } } = await supabase.auth.getUser();
  return user;
}

/**
 * Sign up with email and password
 */
export async function signUp(email: string, password: string, fullName?: string) {
  if (!supabase) throw new Error('Supabase not configured');
  
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: fullName,
      },
    },
  });
  
  if (error) throw error;
  return data;
}

/**
 * Sign in with email and password
 */
export async function signIn(email: string, password: string) {
  if (!supabase) throw new Error('Supabase not configured');
  
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });
  
  if (error) throw error;
  return data;
}

/**
 * Sign in with OAuth provider
 */
export async function signInWithOAuth(provider: 'google' | 'github') {
  if (!supabase) throw new Error('Supabase not configured');

  // Clear any stale local session before OAuth redirect.
  // This prevents reusing an expired token if callback exchange fails.
  await supabase.auth.signOut({ scope: 'local' });

  const { data, error } = await supabase.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: `${window.location.origin}/auth/callback`,
    },
  });
  
  if (error) throw error;
  return data;
}

/**
 * Sign out
 */
export async function signOut() {
  if (!supabase) return;
  
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}

/**
 * Send password reset email
 */
export async function resetPassword(email: string) {
  if (!supabase) throw new Error('Supabase not configured');
  
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/auth/reset-password`,
  });
  
  if (error) throw error;
}

/**
 * Update user password
 */
export async function updatePassword(newPassword: string) {
  if (!supabase) throw new Error('Supabase not configured');
  
  const { error } = await supabase.auth.updateUser({
    password: newPassword,
  });
  
  if (error) throw error;
}

/**
 * Update user profile
 */
export async function updateProfile(data: { full_name?: string; avatar_url?: string }) {
  if (!supabase) throw new Error('Supabase not configured');
  
  const { error } = await supabase.auth.updateUser({
    data,
  });
  
  if (error) throw error;
}

export type { User, Session };
