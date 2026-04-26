export function TutorialPanel() {
  return (
    <div className="max-w-3xl mx-auto p-8 space-y-10">
      <div>
        <h1 className="text-2xl font-bold text-foreground mb-1">RAG Learning Lab — Tutorial</h1>
        <p className="text-muted-foreground text-sm">Kompletny przewodnik uruchomienia i użycia aplikacji.</p>
      </div>

      {/* SEKCJA 1 */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold border-b pb-2">Część 1: Uruchomienie</h2>

        <Step number={1} title="Uzupełnij klucz OpenAI API" done>
          <p>Plik <Code>backend/.env</Code> musi zawierać Twój klucz API:</p>
          <Pre>{`OPENAI_API_KEY=sk-...twój_klucz...
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4o-mini
CHROMA_PERSIST_DIR=./chroma_data`}</Pre>
        </Step>

        <Step number={2} title="Uruchom backend (FastAPI)">
          <p>Otwórz PowerShell w katalogu backendu:</p>
          <Pre>{`cd .worktrees/feature/scaffolding/backend`}</Pre>
          <p className="mt-2">Aktywuj środowisko wirtualne <span className="text-warning font-medium">(PowerShell — nie używaj <Code>source</Code>)</span>:</p>
          <Pre>{`.\\venv\\Scripts\\Activate.ps1`}</Pre>
          <Note>Jeśli pojawi się błąd "cannot be loaded because running scripts is disabled", uruchom raz:<br />
            <code className="text-xs">Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser</code>
          </Note>
          <p className="mt-2">Uruchom serwer:</p>
          <Pre>{`uvicorn main:app --reload --port 8000`}</Pre>
          <p className="text-xs text-muted-foreground mt-1">Backend działa pod <Code>http://localhost:8000</Code> · dokumentacja API: <Code>/docs</Code></p>
        </Step>

        <Step number={3} title="Uruchom frontend (React + Vite)">
          <p>Otwórz drugie okno PowerShell:</p>
          <Pre>{`cd .worktrees/feature/scaffolding/frontend
npm run dev`}</Pre>
          <p className="text-xs text-muted-foreground mt-1">Frontend działa pod <Code>http://localhost:5173</Code></p>
        </Step>
      </section>

      {/* SEKCJA 2 */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold border-b pb-2">Część 2: Pełny pipeline RAG</h2>

        <PipelineStep icon="📄" panel="Documents" title="Wgraj dokument">
          <ol className="list-decimal list-inside space-y-1 text-sm">
            <li>Przeciągnij plik <Code>.txt</Code>, <Code>.pdf</Code> lub <Code>.docx</Code> na strefę uploadu — lub wklej URL bloga w zakładce "From URL"</li>
            <li>Po wgraniu system zapyta, czy przypisać dokument do folderu — wybierz istniejący, utwórz nowy lub pomiń</li>
            <li>Użyj chipów folderów i pola wyszukiwania aby filtrować listę dokumentów</li>
            <li>Kliknij na dokument — zobaczysz podgląd surowego tekstu po prawej</li>
            <li>Kliknij ikonę kosza aby usunąć dokument — zostaniesz poproszony o potwierdzenie, po którym usunięte zostaną też jego chunki i embeddingi</li>
          </ol>
          <Note>Im bardziej spójny i ustrukturyzowany dokument, tym lepsze wyniki retrieval.</Note>
        </PipelineStep>

        <PipelineStep icon="✂️" panel="Chunking Lab" title="Podziel tekst na fragmenty">
          <ol className="list-decimal list-inside space-y-1 text-sm">
            <li>W lewym panelu ustaw strategię: <strong>Fixed Size</strong>, <strong>Recursive</strong> lub <strong>Semantic</strong>, a także suwaki <strong>Chunk Size</strong> i <strong>Overlap</strong></li>
            <li>Zakładka <strong>Kolejka</strong> pokazuje dokumenty bez chunków — kliknij "Chunkuj" przy wybranym dokumencie lub "Chunkuj całą kolejkę" dla wszystkich</li>
            <li>Zakładka <strong>Przeglądaj</strong> pokazuje dokumenty z chunkami — wybierz dokument z listy aby zobaczyć wygenerowane fragmenty i ich statystyki</li>
          </ol>
          <Note>Zbyt duże chunki = mało precyzyjny retrieval. Overlap zapobiega ucinaniu sensu na granicy.</Note>
        </PipelineStep>

        <PipelineStep icon="🔵" panel="Embeddings" title="Wygeneruj embeddingi i wizualizuj">
          <ol className="list-decimal list-inside space-y-1 text-sm">
            <li>Zakładka <strong>Do wygenerowania</strong> pokazuje dokumenty bez embeddingów — kliknij "Embed" przy wybranym dokumencie lub "Wygeneruj wszystkie"</li>
            <li>Zakładka <strong>Wygenerowane</strong> pokazuje dokumenty z embeddingami i scatter plot w 2D</li>
            <li>Kliknij punkt na wykresie — zobaczysz treść chunku</li>
            <li>Kliknij dwa punkty kolejno → zobaczysz cosine similarity (0–1)</li>
          </ol>

          <div className="space-y-2 mt-2">
            <p className="font-medium text-foreground text-sm">Co widzę na wykresie?</p>
            <p>Każdy punkt to jeden chunk tekstu. Jego <strong>pozycja</strong> reprezentuje znaczenie — model OpenAI zamienił każdy fragment w wektor 1536 liczb (tzw. embedding), a PCA spłaszczyło to do 2D żebyś mógł to zobaczyć. Punkty blisko siebie = fragmenty o podobnym znaczeniu.</p>
            <p>Przy 2–3 punktach wykres wygląda pusto — dopiero przy 20+ chunków widać skupiska tematyczne.</p>
          </div>

          <div className="space-y-2 mt-2">
            <p className="font-medium text-foreground text-sm">Co oznacza cosine similarity?</p>
            <p>Miara podobieństwa między dwoma fragmentami: <strong>1.0</strong> = identyczne znaczenie, <strong>0.0</strong> = zupełnie różne, <strong>wartości ujemne</strong> = przeciwstawne. Właśnie tym kryterium RAG wybiera najlepsze chunki do odpowiedzi na Twoje pytanie.</p>
          </div>
        </PipelineStep>

        <PipelineStep icon="💬" panel="Chat" title="Zadaj pytanie i obserwuj pipeline">
          <ol className="list-decimal list-inside space-y-1 text-sm">
            <li>Wpisz pytanie i naciśnij Enter — odpowiedź streamuje się token po tokenie</li>
            <li><strong>Retrieval Panel</strong> — top-K chunków najlepiej pasujących do pytania z cosine similarity</li>
            <li><strong>Prompt Builder</strong> — pełny prompt: system message + kontekst z chunków + zapytanie + token breakdown</li>
            <li>Edytuj system prompt i kliknij <strong>Update</strong></li>
          </ol>
          <Note>Widzisz dokładnie CO model dostaje — to serce edukacyjne RAG Learning Lab.</Note>
        </PipelineStep>

        <PipelineStep icon="📊" panel="Metrics" title="Analizuj metryki sesji">
          <ol className="list-decimal list-inside space-y-1 text-sm">
            <li>Podsumowanie sesji: łączna liczba zapytań, tokeny, koszt w USD</li>
            <li>Tabela zapytań: czas retrieval / embed / LLM, tokeny i koszt per zapytanie</li>
            <li><strong>Clear All Data</strong> — usuwa dokumenty, chunki, embeddingi i historię czatu</li>
          </ol>
        </PipelineStep>
      </section>

      {/* SEKCJA 3 */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold border-b pb-2">Część 3: Rozwiązywanie problemów</h2>
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-muted text-left">
              <th className="px-3 py-2 rounded-tl border border-border">Sytuacja</th>
              <th className="px-3 py-2 rounded-tr border border-border">Rozwiązanie</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["Backend nie startuje — brak modułu", "pip install -r requirements.txt (w aktywowanym venv)"],
              ["\"OPENAI_API_KEY not set\"", "Sprawdź backend/.env — klucz musi zaczynać się od sk-"],
              ["Scatter plot pusty", "Przejdź do zakładki Wygenerowane w sekcji Embeddings — jeśli pusta, najpierw wygeneruj chunki i embeddingi"],
              ["Chat nie odpowiada", "Muszą istnieć embeddingi w ChromaDB — retrieval potrzebuje wektorów"],
              ["Dane po restarcie nadal są", "ChromaDB persystuje w backend/chroma_data/ — użyj Clear All Data"],
              ["Chcę usunąć dokument z bazy", "Kliknij ikonę kosza w sekcji Documents — potwierdzenie usunie dokument razem z chunkami i embeddingami"],
            ].map(([problem, solution]) => (
              <tr key={problem} className="border-b border-border odd:bg-card even:bg-muted/20">
                <td className="px-3 py-2 border border-border font-medium text-warning">{problem}</td>
                <td className="px-3 py-2 border border-border text-foreground">{solution}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* SEKCJA 4 */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold border-b pb-2">Część 4: Testy backendu</h2>
        <Pre>{`cd backend
.\\.venv\\Scripts\\Activate.ps1
pytest tests/ -v`}</Pre>
        <p className="text-sm text-muted-foreground">Oczekiwany wynik: <strong className="text-success">15 passed</strong></p>
      </section>
    </div>
  );
}

/* ---- helpers ---- */

function Step({ number, title, done, children }: { number: number; title: string; done?: boolean; children: React.ReactNode }) {
  return (
    <div className="flex gap-4">
      <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold mt-0.5 ${done ? "bg-success/20 text-success" : "bg-primary/15 text-primary"}`}>
        {done ? "✓" : number}
      </div>
      <div className="flex-1 space-y-2">
        <h3 className="font-medium text-sm text-foreground">{title}</h3>
        <div className="text-sm text-muted-foreground space-y-2">{children}</div>
      </div>
    </div>
  );
}

function PipelineStep({ icon, panel, title, children }: { icon: string; panel: string; title: string; children: React.ReactNode }) {
  return (
    <div className="border border-border rounded-lg p-4 space-y-2 bg-card">
      <div className="flex items-center gap-2">
        <span className="text-lg">{icon}</span>
        <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded text-muted-foreground">{panel}</span>
        <span className="font-medium text-sm text-foreground">{title}</span>
      </div>
      <div className="text-sm text-muted-foreground space-y-2">{children}</div>
    </div>
  );
}

function Pre({ children }: { children: React.ReactNode }) {
  return (
    <pre className="bg-muted text-foreground text-xs rounded p-3 overflow-x-auto font-mono leading-relaxed">
      {children}
    </pre>
  );
}

function Code({ children }: { children: React.ReactNode }) {
  return <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono text-foreground">{children}</code>;
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-warning/10 border border-warning/30 rounded px-3 py-2 text-xs text-warning">
      <span className="font-semibold">Wskazówka: </span>{children}
    </div>
  );
}
