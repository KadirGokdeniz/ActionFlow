import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { TravelContextData } from '@/types';

interface TravelContextType {
  travelData: TravelContextData;
  updateTravelData: (data: Partial<TravelContextData>) => void;
  clearTravelData: () => void;
  hasContext: boolean;
}

const TravelContext = createContext<TravelContextType | undefined>(undefined);

interface TravelProviderProps {
  children: ReactNode;
}

const initialTravelData: TravelContextData = {
  origin: undefined,
  destination: undefined,
  departureDate: undefined,
  returnDate: undefined,
  travelers: undefined,
  budget: undefined,
  tripType: undefined,
};

export function TravelProvider({ children }: TravelProviderProps) {
  const [travelData, setTravelData] = useState<TravelContextData>(initialTravelData);

  const updateTravelData = useCallback((data: Partial<TravelContextData>) => {
    setTravelData((prev) => ({
      ...prev,
      ...data,
    }));
  }, []);

  const clearTravelData = useCallback(() => {
    setTravelData(initialTravelData);
  }, []);

  const hasContext = Boolean(
    travelData.origin ||
      travelData.destination ||
      travelData.departureDate ||
      travelData.returnDate ||
      travelData.travelers ||
      travelData.budget
  );

  const value: TravelContextType = {
    travelData,
    updateTravelData,
    clearTravelData,
    hasContext,
  };

  return <TravelContext.Provider value={value}>{children}</TravelContext.Provider>;
}

export function useTravelContext() {
  const context = useContext(TravelContext);
  if (context === undefined) {
    throw new Error('useTravelContext must be used within a TravelProvider');
  }
  return context;
}
