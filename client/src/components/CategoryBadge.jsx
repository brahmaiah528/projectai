import React from 'react';
import { 
  AlertTriangle, Star, Tag, Landmark, Briefcase, 
  GraduationCap, ShoppingBag, Users, User, RefreshCw, ShieldCheck, HelpCircle,
  Building2, HeadphonesIcon, CalendarCheck, Plane, Heart, Newspaper, Zap,
  CreditCard, BookOpen, Calendar
} from 'lucide-react';

const CATEGORY_STYLES = {
  'Immediate Reply': { bg: 'bg-red-500/20 text-red-700 dark:text-red-300 border-red-500/40 font-bold shadow-sm animate-pulse', icon: Zap },
  Spam:            { bg: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',       icon: AlertTriangle },
  Important:       { bg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',   icon: Star },
  Promotions:      { bg: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20', icon: Tag },
  Banking:         { bg: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20', icon: Landmark },
  Jobs:            { bg: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',       icon: Briefcase },
  Examinations:    { bg: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20', icon: GraduationCap },
  Purchases:       { bg: 'bg-teal-500/10 text-teal-600 dark:text-teal-400 border-teal-500/20',       icon: ShoppingBag },
  Social:          { bg: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20',           icon: Users },
  Personal:        { bg: 'bg-pink-500/10 text-pink-600 dark:text-pink-400 border-pink-500/20',       icon: User },
  Updates:         { bg: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20',       icon: RefreshCw },
  Office:          { bg: 'bg-slate-500/10 text-slate-700 dark:text-slate-300 border-slate-500/20',   icon: Building2 },
  'Customer Support': { bg: 'bg-lime-500/10 text-lime-700 dark:text-lime-400 border-lime-500/20',   icon: HeadphonesIcon },
  Bookings:        { bg: 'bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20', icon: CalendarCheck },
  Travel:          { bg: 'bg-fuchsia-500/10 text-fuchsia-600 dark:text-fuchsia-400 border-fuchsia-500/20', icon: Plane },
  Healthcare:      { bg: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',           icon: Heart },
  Newsletters:     { bg: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20', icon: Newspaper },
  Others:          { bg: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20',   icon: HelpCircle },
};

export default function CategoryBadge({ category, size = 'sm' }) {
  const style = CATEGORY_STYLES[category] || CATEGORY_STYLES.Others;
  const IconComponent = style.icon;

  const sizeClasses = size === 'xs' 
    ? 'px-2 py-0.5 text-[11px]' 
    : size === 'lg' 
    ? 'px-3 py-1.5 text-sm font-semibold' 
    : 'px-2.5 py-1 text-xs font-medium';

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border ${style.bg} ${sizeClasses}`}>
      <IconComponent className={size === 'xs' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      <span>{category}</span>
    </span>
  );
}

export function PriorityActionBadge({ highlight, size = 'sm' }) {
  if (!highlight) return null;
  const { type, label } = highlight;
  
  let bgStyle = 'bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/40 animate-pulse';
  let Icon = Zap;
  
  if (type === 'payment_due') {
    bgStyle = 'bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/40 font-bold';
    Icon = CreditCard;
  } else if (type === 'exam_assignment') {
    bgStyle = 'bg-amber-500/15 text-amber-800 dark:text-amber-300 border-amber-500/40 font-bold';
    Icon = BookOpen;
  } else if (type === 'work_deadline') {
    bgStyle = 'bg-orange-500/15 text-orange-800 dark:text-orange-300 border-orange-500/40 font-bold';
    Icon = Briefcase;
  } else if (type === 'appointment') {
    bgStyle = 'bg-purple-500/15 text-purple-700 dark:text-purple-300 border-purple-500/40 font-bold';
    Icon = Calendar;
  } else if (type === 'immediate_reply') {
    bgStyle = 'bg-red-500/20 text-red-700 dark:text-red-300 border-red-500/40 font-bold shadow-sm animate-pulse';
    Icon = Zap;
  }

  const sizeClasses = size === 'xs' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-lg border ${bgStyle} ${sizeClasses}`}>
      <Icon className="w-3.5 h-3.5" />
      <span>{label}</span>
    </span>
  );
}
