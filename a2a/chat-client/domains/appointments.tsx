/*
 * Copyright 2026 UCP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * Appointment domain — response handlers and renderers for locations,
 * staff, availability slots, services, and bookings.
 */

import type React from 'react';
import AvailabilitySlots from '../components/AvailabilitySlots';
import BookingCard from '../components/BookingCard';
import LocationCard from '../components/LocationCard';
import ServiceCard from '../components/ServiceCard';
import type {
  AvailabilitySlot,
  Booking,
  ChatMessage,
  Location,
  ServiceVariation,
  StaffResponse,
} from '../types';
import type {ResponseHandler} from './registry';

// ---------------------------------------------------------------------------
// Response handlers
// ---------------------------------------------------------------------------

export const appointmentResponseHandlers: ResponseHandler[] = [
  {
    dataKey: 'a2a.service_results',
    parse: (data: unknown) => ({services: data as ServiceVariation[]}),
  },
  {
    dataKey: 'a2a.locations',
    parse: (data: unknown) => ({locations: data as Location[]}),
  },
  {
    dataKey: 'a2a.staff',
    parse: (data: unknown) => ({staff: data as StaffResponse[]}),
  },
  {
    dataKey: 'a2a.availability_slots',
    parse: (data: unknown) => ({availabilitySlots: data as AvailabilitySlot[]}),
  },
  {
    dataKey: 'a2a.bookings',
    parse: (data: unknown) => ({bookings: data as Booking[]}),
  },
];

export function appointmentHasContent(msg: ChatMessage): boolean {
  return !!(
    msg.services ||
    msg.locations ||
    msg.availabilitySlots ||
    msg.bookings
  );
}

// ---------------------------------------------------------------------------
// Renderer
// ---------------------------------------------------------------------------

export interface AppointmentRendererProps {
  message: ChatMessage;
  onAddServiceToCheckout?: (service: ServiceVariation) => void;
  onSelectLocation?: (locationId: string) => void;
  onSelectTimeSlot?: (slot: AvailabilitySlot) => void;
}

export const AppointmentRenderer: React.FC<AppointmentRendererProps> = ({
  message,
  onAddServiceToCheckout,
  onSelectLocation,
  onSelectTimeSlot,
}) => {
  return (
    <>
      {message.services && message.services.length > 0 && (
        <div className="w-full my-1 overflow-x-auto">
          <div className="flex space-x-4 p-2">
            {message.services.map((service) => (
              <ServiceCard
                key={service.id}
                service={service}
                onAddToCheckout={onAddServiceToCheckout}
              />
            ))}
          </div>
        </div>
      )}

      {message.locations && message.locations.length > 0 && (
        <div className="w-full my-1 overflow-x-auto">
          <div className="flex space-x-4 p-2">
            {message.locations.map((location) => (
              <LocationCard
                key={location.id}
                location={location}
                onSelect={onSelectLocation}
              />
            ))}
          </div>
        </div>
      )}

      {message.availabilitySlots && message.availabilitySlots.length > 0 && (
        <div className="w-full my-1">
          <AvailabilitySlots
            slots={message.availabilitySlots}
            onSelectSlot={onSelectTimeSlot}
          />
        </div>
      )}

      {message.bookings && message.bookings.length > 0 && (
        <div className="w-full my-1 space-y-4">
          {message.bookings.map((booking) => (
            <BookingCard key={booking.id} booking={booking} />
          ))}
        </div>
      )}
    </>
  );
};
