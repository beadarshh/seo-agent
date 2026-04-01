import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { url, title, content, headings, keyword, user_email, meta_tags, elements, images } = await req.json()
    
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // 1. Store the page
    const { data: pageData, error: pageError } = await supabaseClient
      .from('pages')
      .upsert({
        user_email,
        url,
        title,
        content,
        target_keyword: keyword,
        headings,
        updated_at: new Date().toISOString()
      }, { onConflict: 'user_email, url' })
      .select()
      .single()

    if (pageError) throw pageError
    const page_id = pageData.id

    // 2. Call Groq for analysis
    const groqApiKey = Deno.env.get('GROQ_API_KEY')
    const systemPrompt = `You are an elite SEO auditor. 
    Audit this content: ${url} | ${title} | ${keyword}
    Content Preview: ${content.substring(0, 3000)}
    
    Return ONLY a JSON array of 5-10 high priority suggestions.
    FORMAT: [{ "suggestion_type": "title|meta|heading|tags", "priority": "high", "current_value": "...", "suggested_value": "...", "reason": "..." }]`

    const aiRes = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${groqApiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [{ role: "user", content: systemPrompt }],
        temperature: 0.1
      })
    })

    const aiData = await aiRes.json()
    const rawSuggestions = aiData.choices[0].message.content
    const jsonMatch = rawSuggestions.match(/\[\s*\{.*\}\s*\]/s)
    const suggestions = JSON.parse(jsonMatch ? jsonMatch[0] : "[]")

    // 3. Store Suggestions
    const dbSuggestions = suggestions.map((s: any) => ({
      page_id,
      type: s.suggestion_type,
      priority: s.priority,
      original_value: s.current_value,
      suggested_value: s.suggested_value,
      reason: s.reason
    }))

    await supabaseClient.from('suggestions').insert(dbSuggestions)

    // 4. Simple Score Calculation
    const penalty = suggestions.reduce((acc: number, s: any) => acc + (s.priority === 'high' ? 20 : 10), 0)
    const seo_score = Math.max(0, 100 - penalty)
    
    await supabaseClient.from('pages').update({ seo_score }).eq('id', page_id)

    return new Response(JSON.stringify({
      page_id,
      seo_score,
      suggestions: suggestions
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    })

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400,
    })
  }
})
