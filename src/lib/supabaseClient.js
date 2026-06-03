import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// Esto nos va a confesar en la consola qué está leyendo React
console.log("URL de Supabase detectada:", supabaseUrl)
console.log("Anon Key detectada:", supabaseAnonKey ? "Existe Key ✅" : "No existe Key ❌")

export const supabase = createClient(supabaseUrl, supabaseAnonKey)