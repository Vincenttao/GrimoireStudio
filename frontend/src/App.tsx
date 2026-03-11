import { Route, Switch } from 'wouter';
import Sidebar from './components/Sidebar';
import MusePage from './pages/MusePage';
import StoryboardPage from './pages/StoryboardPage';
import CharactersPage from './pages/CharactersPage';
import ArchivePage from './pages/ArchivePage';
import SettingsPage from './pages/SettingsPage';

function App() {
  return (
    <div className="flex h-screen w-screen bg-grimoire-bg overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-hidden">
        <Switch>
          <Route path="/" component={MusePage} />
          <Route path="/storyboard" component={StoryboardPage} />
          <Route path="/characters" component={CharactersPage} />
          <Route path="/archive" component={ArchivePage} />
          <Route path="/settings" component={SettingsPage} />
        </Switch>
      </main>
    </div>
  );
}

export default App;
