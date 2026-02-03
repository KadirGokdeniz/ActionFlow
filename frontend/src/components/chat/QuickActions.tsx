import React from 'react';
import { motion } from 'framer-motion';
import { Plane, Hotel, CalendarCheck, XCircle, DollarSign, HelpCircle } from 'lucide-react';
import { useUI } from '@/contexts/UIContext';
import { cn } from '@/lib/utils';

interface QuickAction {
  id: string;
  icon: React.ReactNode;
  labelTr: string;
  labelEn: string;
  message: string;
}

const quickActions: QuickAction[] = [
  {
    id: 'flights',
    icon: <Plane className="h-4 w-4" />,
    labelTr: 'Uçuş Ara',
    labelEn: 'Search Flights',
    message: 'Uçuş aramak istiyorum',
  },
  {
    id: 'hotels',
    icon: <Hotel className="h-4 w-4" />,
    labelTr: 'Otel Bul',
    labelEn: 'Find Hotels',
    message: 'Otel aramak istiyorum',
  },
  {
    id: 'bookings',
    icon: <CalendarCheck className="h-4 w-4" />,
    labelTr: 'Rezervasyonlarım',
    labelEn: 'My Bookings',
    message: 'Rezervasyonlarımı görmek istiyorum',
  },
  {
    id: 'cancel',
    icon: <XCircle className="h-4 w-4" />,
    labelTr: 'İptal Et',
    labelEn: 'Cancel',
    message: 'Rezervasyonumu iptal etmek istiyorum',
  },
  {
    id: 'refund',
    icon: <DollarSign className="h-4 w-4" />,
    labelTr: 'İade Durumu',
    labelEn: 'Refund Status',
    message: 'İade durumumu öğrenmek istiyorum',
  },
  {
    id: 'policies',
    icon: <HelpCircle className="h-4 w-4" />,
    labelTr: 'Politikalar',
    labelEn: 'Policies',
    message: 'Seyahat politikaları hakkında bilgi almak istiyorum',
  },
];

interface QuickActionsProps {
  onAction: (message: string) => void;
  disabled?: boolean;
}

export function QuickActions({ onAction, disabled = false }: QuickActionsProps) {
  const { language } = useUI();

  return (
    <div className="flex gap-2 overflow-x-auto pb-2 custom-scrollbar">
      {quickActions.map((action, index) => (
        <motion.button
          key={action.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => onAction(action.message)}
          disabled={disabled}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-full',
            'bg-card/50 backdrop-blur-sm border border-border/50',
            'text-sm font-medium text-foreground',
            'hover:bg-card hover:border-primary/30 hover:shadow-md',
            'transition-all duration-200',
            'whitespace-nowrap flex-shrink-0',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <span className="text-primary">{action.icon}</span>
          <span>{language === 'tr' ? action.labelTr : action.labelEn}</span>
        </motion.button>
      ))}
    </div>
  );
}
