import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-semibold transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-petrol-500/40 disabled:pointer-events-none disabled:opacity-50 cursor-pointer motion-reduce:transition-none',
  {
    variants: {
      variant: {
        default:
          'bg-petrol-600 text-white hover:bg-petrol-500',
        secondary:
          'bg-white text-graphite-700 border border-graphite-200 hover:bg-graphite-50',
        ghost: 'text-graphite-600 hover:bg-graphite-100',
        destructive: 'bg-error text-white hover:bg-red-600',
        outline:
          'border border-petrol-300 text-petrol-700 bg-petrol-50 hover:bg-petrol-100',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-8 rounded-md px-3 text-xs',
        lg: 'h-11 rounded-lg px-6',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  ),
)
Button.displayName = 'Button'

export { buttonVariants }
