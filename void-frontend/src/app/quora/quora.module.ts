import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AccountsDashboardComponent } from './accounts-dashboard/accounts-dashboard.component';
import { QuestionsTableComponent } from './questions-table/questions-table.component';
import { RouterModule, Routes } from '@angular/router';
import { QuoraService } from './quora.service';
import { SharedModule } from '../shared/shared.module';
import { ReactiveFormsModule } from '@angular/forms';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatButtonToggleModule } from '@angular/material/button-toggle';


export const QuoraRoutes: Routes = [
  { path: 'quora', children: [
      { path: 'questions-table', component: QuestionsTableComponent, pathMatch: 'full' },
      { path: 'accounts-dashboard', component: AccountsDashboardComponent, pathMatch: 'full' }
    ]
  }
];

@NgModule({
  declarations: [
    QuestionsTableComponent,
    AccountsDashboardComponent
  ],
  imports: [
    CommonModule,
    RouterModule.forChild(QuoraRoutes),
    SharedModule,
    ReactiveFormsModule,
    MatSlideToggleModule,
    MatButtonToggleModule
  ],
  exports : [
    RouterModule
  ],
  providers : [
    QuoraService
  ]
})
export class QuoraModule { }
