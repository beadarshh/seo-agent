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
    const { user_email } = await req.json()
    
    // Initialize Supabase
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // 1. Fetch user's latest pages and suggestions
    const { data: pages } = await supabaseClient
      .from('pages')
      .select('id, title, url, seo_score, content')
      .eq('user_email', user_email)
      .order('updated_at', { ascending: false })
      .limit(10)

    if (!pages || pages.length === 0) {
      throw new Error("No pages found for this user.")
    }

    // 2. Aggregate Gaps (Simple LLM analysis of the list)
    const contentSummary = pages.map(p => `Page: ${p.url} | Score: ${p.seo_score}`).join('\n')
    
    const groqApiKey = Deno.env.get('GROQ_API_KEY')
    const systemPrompt = `You are a Senior SEO Strategist. 
    Review these 10 pages and identify the biggest common "SEO Gaps" for this user.
    Summary of Pages: ${contentSummary}
    
    Return a bi-weekly Performance Gap Report in JSON format:
    {
      "overall_score": 70,
      "gap_suggestions": ["List item 1", "List item 2"]
    }`

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
    const report = JSON.parse(aiData.choices[0].message.content.match(/\{.*\}/s)[0])

    // 3. Store the report
    await supabaseClient.from('two_week_reports').insert({
      page_id: pages[0].id,
      overall_score: report.overall_score,
      gap_suggestions: report.gap_suggestions
    })

    return new Response(JSON.stringify(report), {
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
