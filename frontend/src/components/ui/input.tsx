import { forwardRef, type InputHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        'flex h-10 w-full rounded-lg border border-graphite-200 bg-white px-3 py-2 text-sm text-graphite-800 placeholder:text-graphite-400 transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-petrol-500/30 focus-visible:border-petrol-400 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none',
        className,
      )}
      {...props}
    />
  ),
)
Input.displayName = 'Input'

export const Label = forwardRef<
  HTMLLabelElement,
  React.LabelHTMLAttributes<HTMLLabelElement> & { required?: boolean }
>(({ className, required, children, ...props }, ref) => (
  <label
    ref={ref}
    className={cn('text-sm font-medium text-graphite-700', className)}
    {...props}
  >
    {children}
    {required && <span className="text-error ml-0.5">*</span>}
  </label>
))
Label.displayName = 'Label'

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      'flex min-h-[100px] w-full rounded-lg border border-graphite-200 bg-white px-3 py-2 text-sm text-graphite-800 placeholder:text-graphite-400 transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-petrol-500/30 focus-visible:border-petrol-400 disabled:cursor-not-allowed disabled:opacity-50 resize-y motion-reduce:transition-none',
      className,
    )}
    {...props}
  />
))
Textarea.displayName = 'Textarea'

export const Select = forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      'flex h-10 w-full rounded-lg border border-graphite-200 bg-white px-3 py-2 text-sm text-graphite-800 transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-petrol-500/30 focus-visible:border-petrol-400 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none',
      className,
    )}
    {...props}
  >
    {children}
  </select>
))
Select.displayName = 'Select'
