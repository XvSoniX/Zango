import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'

export function RootView() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Shadcn/ui Verification</CardTitle>
          <CardDescription>Minimal component integration verification harness.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input placeholder="Verification input field" />
          <div className="flex gap-2">
            <Button variant="default">Action Button</Button>
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline">Open Dialog</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Dialog Verification</DialogTitle>
                  <DialogDescription>
                    Dialog component rendered and mounted successfully.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <DialogClose asChild>
                    <Button variant="outline">Dismiss</Button>
                  </DialogClose>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
        <CardFooter className="justify-between text-xs text-muted-foreground">
          <span>Button, Input, Card, Dialog verified</span>
        </CardFooter>
      </Card>
    </main>
  )
}
