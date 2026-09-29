import { AvailabilityEditor } from '../components/calendar/AvailabilityEditor';
import { BlockEditor } from '../components/calendar/BlockEditor';
import { DaySlotsPanel } from '../components/calendar/DaySlotsPanel';
import { PageHeader } from '../components/Primitives';

export function CalendarPage() {
  return (
    <div>
      <PageHeader
        title="Calendar"
        subtitle="Your availability, blocked time and interviews."
      />
      <div className="space-y-5">
        <DaySlotsPanel />
        <AvailabilityEditor />
        <BlockEditor />
      </div>
    </div>
  );
}
