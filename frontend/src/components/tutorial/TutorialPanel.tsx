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
          <p className="mt-2">Aktywuj środowisko wirtualne <span className="text-amber-600 font-medium">(PowerShell — nie używaj <Code>source</Code>)</span>:</p>
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
            <li>Przeciągnij plik <Code>.txt</Code>, <Code>.pdf</Code> lub <Code>.docx</Code> na strefę uploadu</li>
            <li>Dokument pojawi się na liście z nazwą, rozmiarem i liczbą znaków</li>
            <li>Kliknij na dokument — zobaczysz podgląd surowego tekstu po prawej</li>
          </ol>
          <Note>Im bardziej spójny i ustrukturyzowany dokument, tym lepsze wyniki retrieval.</Note>
        </PipelineStep>

        <PipelineStep icon="✂️" panel="Chunking Lab" title="Podziel tekst na fragmenty">
          <ol className="list-decimal list-inside space-y-1 text-sm">
            <li>Wybierz dokument z listy</li>
            <li>Wybierz strategię: <strong>Fixed Size</strong> (co N znaków), <strong>Recursive</strong> (po separatorach), <strong>Semantic</strong> (po zdaniach)</li>
            <li>Ustaw suwaki <strong>Chunk Size</strong> i <strong>Overlap %</strong></li>
            <li>Kliknij <strong>Generate Chunks</strong> — zobaczysz statystyki i kolorowe bloki tekstu</li>
          </ol>
          <Note>Zbyt duże chunki = mało precyzyjny retrieval. Overlap zapobiega ucinaniu sensu na granicy.</Note>
        </PipelineStep>

        <PipelineStep icon="🔵" panel="Embeddings" title="Wygeneruj embeddingi i wizualizuj">
          <ol className="list-decimal list-inside space-y-1 text-sm">
            <li>Wybierz dokument (musi mieć wygenerowane chunki)</li>
            <li>Kliknij <strong>Generate Embeddings</strong> — każdy chunk trafia do OpenAI, który zamienia go w wektor 1536 liczb, a potem do ChromaDB</li>
            <li>Scatter plot pokazuje chunki jako punkty w 2D</li>
            <li>Kliknij punkt — zobaczysz treść chunku</li>
            <li>Kliknij dwa punkty kolejno → zobaczysz cosine similarity (0–1)</li>
          </ol>

          <div className="space-y-2 mt-2">
            <p className="font-medium text-foreground text-sm">Co widzę na wykresie?</p>
            <p>Każdy punkt to jeden chunk tekstu. Jego <strong>pozycja</strong> reprezentuje znaczenie — model OpenAI zamienił każdy fragment w wektor 1536 liczb (tzw. embedding), a PCA spłaszczyło to do 2D żebyś mógł to zobaczyć. Punkty blisko siebie = fragmenty o podobnym znaczeniu. Punkty daleko = tematycznie różne.</p>
            <p>Przy 2–3 punktach wykres wygląda pusto — dopiero przy 20+ chunków widać skupiska tematyczne i różnice między dokumentami.</p>
          </div>

          <div className="space-y-2 mt-2">
            <p className="font-medium text-foreground text-sm">Co oznacza cosine similarity?</p>
            <p>Miara podobieństwa między dwoma fragmentami: <strong>1.0</strong> = identyczne znaczenie, <strong>0.0</strong> = zupełnie różne, <strong>wartości ujemne</strong> = przeciwstawne. Właśnie tym kryterium RAG wybiera najlepsze chunki do odpowiedzi na Twoje pytanie.</p>
          </div>

          <Note>Ten sam tekst → zawsze ten sam wektor (model jest deterministyczny). Nie klikaj Generate Embeddings dwa razy na tym samym dokumencie — tworzysz duplikaty w ChromaDB. Jeśli to zrobiłeś, użyj Clear All Data i zacznij od nowa.</Note>
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
              ["Scatter plot pusty", "Najpierw wygeneruj chunki (panel 2), potem embeddingi (panel 3)"],
              ["Chat nie odpowiada", "Muszą istnieć embeddingi w ChromaDB — retrieval potrzebuje wektorów"],
              ["Dane po restarcie nadal są", "ChromaDB persystuje w backend/chroma_data/ — użyj Clear All Data"],
            ].map(([problem, solution]) => (
              <tr key={problem} className="border-b border-border odd:bg-white even:bg-muted/30">
                <td className="px-3 py-2 border border-border font-medium text-amber-700">{problem}</td>
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
        <p className="text-sm text-muted-foreground">Oczekiwany wynik: <strong className="text-green-600">15 passed</strong></p>
      </section>
    </div>
  );
}

/* ---- helpers ---- */

function Step({ number, title, done, children }: { number: number; title: string; done?: boolean; children: React.ReactNode }) {
  return (
    <div className="flex gap-4">
      <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold mt-0.5 ${done ? "bg-green-100 text-green-700" : "bg-primary/10 text-primary"}`}>
        {done ? "✓" : number}
      </div>
      <div className="flex-1 space-y-2">
        <h3 className="font-medium text-sm">{title}</h3>
        <div className="text-sm text-muted-foreground space-y-2">{children}</div>
      </div>
    </div>
  );
}

function PipelineStep({ icon, panel, title, children }: { icon: string; panel: string; title: string; children: React.ReactNode }) {
  return (
    <div className="border border-border rounded-lg p-4 space-y-2 bg-white">
      <div className="flex items-center gap-2">
        <span className="text-lg">{icon}</span>
        <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded text-muted-foreground">{panel}</span>
        <span className="font-medium text-sm">{title}</span>
      </div>
      <div className="text-sm text-muted-foreground space-y-2">{children}</div>
    </div>
  );
}

function Pre({ children }: { children: React.ReactNode }) {
  return (
    <pre className="bg-zinc-900 text-zinc-100 text-xs rounded p-3 overflow-x-auto font-mono leading-relaxed">
      {children}
    </pre>
  );
}

function Code({ children }: { children: React.ReactNode }) {
  return <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono text-foreground">{children}</code>;
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded px-3 py-2 text-xs text-amber-800">
      <span className="font-semibold">Wskazówka: </span>{children}
    </div>
  );
}
