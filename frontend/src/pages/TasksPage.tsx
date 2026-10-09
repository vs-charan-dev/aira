import { TaskBoard } from '../components/companion/TaskBoard';
import { useEffect } from 'react';
export function TasksPage() {
  useEffect(() => { document.title = 'AIRA · Tasks'; }, []);
  return <TaskBoard floating />;
}
