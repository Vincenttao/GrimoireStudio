import { useEffect } from 'react';
import { Route, Switch, Redirect } from 'wouter';
import Sidebar from './components/Sidebar';
import MusePanel from './components/MusePanel';
import StoryboardPage from './pages/StoryboardPage';
import CharactersPage from './pages/CharactersPage';
import ArchivePage from './pages/ArchivePage';
import SettingsPage from './pages/SettingsPage';
import { wsManager } from './lib/ws';

function App() {
  useEffect(() => {
    wsManager.connect();
    return () => wsManager.disconnect();
  }, []);

  return (
    <div className="flex h-screen w-screen bg-grimoire-bg overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-hidden">
        <Switch>
          <Route path="/storyboard" component={StoryboardPage} />
          <Route path="/characters" component={CharactersPage} />
          <Route path="/archive" component={ArchivePage} />
          <Route path="/settings" component={SettingsPage} />
          <Route path="/">
            <Redirect to="/storyboard" />
          </Route>
        </Switch>
      </main>
      <MusePanel />
    </div>
  );
}

export default App;
